import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
from geopy.geocoders import ArcGIS

# 🔗 連結你的雲端大腦
API_URL = "https://my-rescue-api-v1.onrender.com"
geolocator = ArcGIS()

st.set_page_config(page_title="E-Rescue 生活救援", page_icon="📱", layout="centered")
st.title("🚗 E-Rescue 全方位生活救援 APP")

# 🧠 路線 B 核心：給網頁加上「記憶力」，記住使用者的訂單！
if "order_id" not in st.session_state:
    st.session_state.order_id = None
if "order_status" not in st.session_state:
    st.session_state.order_status = "pending"

tab_client, tab_provider = st.tabs(["🙋‍♂️ 我是客戶 (叫修)", "🦸‍♂️ 我是師傅 (接單)"])

# ==========================================
# 分頁 1：客戶端畫面 (路線A 互動地圖 + 路線B 狀態追蹤)
# ==========================================
with tab_client:
    # 🌟 情境 1：還沒有叫車，顯示「地圖與表單」
    if st.session_state.order_id is None:
        st.markdown("### 📍 步驟 1：在地圖上點擊您的救援位置")
        st.info("💡 提示：您可以用滑鼠/手指拖曳地圖，並直接點擊您所在的準確位置。")

        # --- 路線 A 核心：建立真正的可點擊互動地圖 ---
        m = folium.Map(location=[24.16, 120.68], zoom_start=14)
        m.add_child(folium.LatLngPopup())  # 開啟點擊獲取經緯度的功能

        # 將地圖顯示在網頁上，並捕捉使用者的點擊座標
        map_data = st_folium(m, height=350, width=700)

        # 預設座標 (台中)
        target_lat, target_lng = 24.16, 120.68

        # 如果使用者有點擊地圖，就把座標抓出來
        if map_data and map_data.get("last_clicked"):
            target_lat = map_data["last_clicked"]["lat"]
            target_lng = map_data["last_clicked"]["lng"]
            st.success(f"📍 已精準鎖定座標：緯度 {target_lat:.4f}, 經度 {target_lng:.4f}")
        else:
            st.warning("👆 請先在地圖上點擊一下您的確切位置喔！")

        # --- 叫車表單 ---
        with st.form("request_form"):
            category = st.selectbox("1️⃣ 需要什麼服務？", ["機車拋錨", "水電問題", "園藝問題", "開鎖服務", "其他"])
            description = st.text_area("2️⃣ 請簡單描述狀況 (點擊上方地圖即可定位)")
            submitted = st.form_submit_button("🚨 立即呼叫救援")

            if submitted:
                if not description:
                    st.warning("請填寫狀況描述喔！")
                elif not map_data or not map_data.get("last_clicked"):
                    st.error("請務必先在地圖上點擊一個位置！")
                else:
                    with st.spinner("系統正在發送訂單..."):
                        payload = {
                            "description": description,
                            "req_lng": target_lng,
                            "req_lat": target_lat,
                            "user_id": "VIP客戶_001",
                            "category": category
                        }
                        try:
                            res = requests.post(f"{API_URL}/requests", json=payload)
                            if res.status_code == 200:
                                # 💡 記住訂單編號，準備切換到「追蹤畫面」
                                data = res.json()
                                st.session_state.order_id = data.get("request_id")
                                st.session_state.order_status = "pending"
                                st.rerun()  # 強制網頁重新整理，切換畫面！
                            else:
                                st.error("❌ 呼叫失敗！")
                        except Exception as e:
                            st.error(f"連線錯誤：{e}")

    # 🌟 情境 2：已經叫車了，顯示「即時狀態追蹤畫面」
    else:
        st.markdown("### 🚁 救援小組派遣中...")
        st.write(f"**您的專屬訂單編號：** `{st.session_state.order_id[:8]}...`")

        # 顯示不同的進度條與狀態
        if st.session_state.order_status == "pending":
            st.warning("⏳ 正在等待附近的專業師傅接單...")
            st.progress(30)
        elif st.session_state.order_status == "accepted":
            st.success("🎉 熱血師傅已接單！正在火速趕往您的位置！")
            st.progress(100)
            st.balloons()

        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 檢查最新狀態"):
                with st.spinner("連線大腦確認中..."):
                    try:
                        # 🕵️‍♂️ 天才繞道法：我們去檢查這張單還在不在「待處理任務牆」上
                        # 如果不在了，就代表它剛剛被某個師傅接走了！
                        check_res = requests.get(f"{API_URL}/provider/requests")
                        if check_res.status_code == 200:
                            all_tasks = check_res.json()
                            still_pending = any(task["request_id"] == st.session_state.order_id for task in all_tasks)

                            if not still_pending:
                                st.session_state.order_status = "accepted"
                            st.rerun()
                    except:
                        st.error("查詢失敗")

        with col2:
            if st.button("❌ 完成救援 / 重新呼叫"):
                # 清除記憶，回到叫車畫面
                st.session_state.order_id = None
                st.session_state.order_status = "pending"
                st.rerun()

# ==========================================
# 分頁 2：師傅端畫面 (維持原樣，但體驗會大升級)
# ==========================================
with tab_provider:
    st.markdown("### 📋 專屬任務牆")
    st.info("系統會自動幫您過濾出符合您專業，且尚未被接走的訂單。")

    my_skill = st.selectbox("請選擇您的專業領域：", ["機車拋錨", "水電問題", "園藝問題", "開鎖服務", "其他"])
    st.button("🔄 刷新任務牆")

    try:
        res = requests.get(f"{API_URL}/provider/requests", params={"category": my_skill})

        if res.status_code == 200:
            tasks = res.json()
            if len(tasks) == 0:
                st.warning("目前沒有符合您專業的待處理訂單喔！去喝杯咖啡吧 ☕")
            else:
                st.success(f"發現 {len(tasks)} 筆新任務！")

                for task in tasks:
                    with st.container():
                        st.markdown("---")
                        st.markdown(f"**📝 狀況：** {task['description']}")
                        st.markdown(f"**🆔 訂單：** `{task['request_id'][:8]}...`")

                        map_data = [{"lat": task["req_lat"], "lon": task["req_lng"]}]
                        st.map(map_data, zoom=15)

                        if st.button(f"✅ 點我接單！", key=f"btn_{task['request_id']}"):
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