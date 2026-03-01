import streamlit as st
import requests

# 🔗 連結你的雲端大腦 (記得換成你的 Render 網址！)
API_URL = ("https://my-rescue-api-v1.onrender.com" )

# --- 畫面外觀設定 ---
st.set_page_config(page_title="生活大管家 APP", page_icon="📱", layout="centered")
st.title("🚗 全方位生活救援 APP")

# 建立兩個分頁按鈕，讓你輕鬆切換身分
tab_client, tab_provider = st.tabs(["🙋‍♂️ 我是客戶 (叫修)", "🦸‍♂️ 我是師傅 (接單)"])

# ==========================================
# 分頁 1：客戶端畫面 (你剛才成功放氣球的地方)
# ==========================================
with tab_client:
    st.markdown("### 遇到困難了嗎？馬上呼叫專業師傅！")
    with st.form("request_form"):
        category = st.selectbox("1️⃣ 需要什麼服務？", ["機車拋錨", "水電問題", "園藝問題", "開鎖服務", "其他"])
        description = st.text_area("2️⃣ 請簡單描述狀況")
        submitted = st.form_submit_button("🚨 立即呼叫救援")

        if submitted:
            if not description:
                st.warning("請填寫狀況描述喔！")
            else:
                payload = {
                    "description": description,
                    "req_lng": 120.68, "req_lat": 24.16,
                    "user_id": "VIP客戶_001",
                    "category": category
                }
                res = requests.post(f"{API_URL}/requests", json=payload)
                if res.status_code == 200:
                    st.success("✅ 呼叫成功！系統正在為您媒合師傅...")
                    st.balloons()

# ==========================================
# ==========================================
# 分頁 2：師傅端畫面 (破解按鈕陷阱版)
# ==========================================
with tab_provider:
    st.markdown("### 📋 專屬任務牆")
    st.info("系統會自動幫您過濾出符合您專業，且尚未被接走的訂單。")

    # 讓師傅選擇自己的專業
    my_skill = st.selectbox("請選擇您的專業領域：", ["機車拋錨", "水電問題", "園藝問題", "開鎖服務", "其他"])

    # 這個按鈕純粹用來「強制重新整理網頁」，我們不再把它當成 if 條件了！
    st.button("🔄 刷新任務牆")

    # --- 直接呼叫 API，不再被包在按鈕裡面 ---
    try:
        res = requests.get(f"{API_URL}/provider/requests", params={"category": my_skill})

        if res.status_code == 200:
            tasks = res.json()
            if len(tasks) == 0:
                st.warning("目前沒有符合您專業的待處理訂單喔！去喝杯咖啡吧 ☕")
            else:
                st.success(f"發現 {len(tasks)} 筆新任務！")

                # 用迴圈把每一筆訂單畫成一個精美的卡片
                for task in tasks:
                    # 用一個框框把卡片包起來，比較好看
                    with st.container():
                        st.markdown("---")  # 畫一條分隔線
                        st.markdown(f"**📝 狀況：** {task['description']}")
                        st.markdown(f"**🆔 訂單：** `{task['request_id'][:8]}...`")
                        # 🗺️ 加上這三行，立刻召喚地圖！
                        map_data = [{"lat": task["req_lat"], "lon": task["req_lng"]}]
                        st.map(map_data, zoom=14)
                        st.markdown("---")  # 再畫一條線隔開按鈕


                        # 這裡的接單按鈕現在絕對點得動了！
                        if st.button(f"✅ 點我接單！", key=f"btn_{task['request_id']}"):
                            # 呼叫 API 的接單功能
                            accept_res = requests.put(
                                f"{API_URL}/provider/requests/{task['request_id']}/accept",
                                params={"provider_id": "熱血師傅_阿明"}
                            )
                            if accept_res.status_code == 200:
                                st.success("🎉 接單成功！請盡速趕往現場！(請按上方按鈕刷新)")
                            else:
                                st.error(f"接單失敗：{accept_res.text}")
        else:
            st.error("無法取得任務列表，請檢查您的 API 狀態。")
    except Exception as e:
        st.error(f"連線發生錯誤：{e}")