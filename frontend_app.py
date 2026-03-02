import streamlit as st
import requests
from geopy.geocoders import Nominatim

# 🔗 連結你的雲端大腦 (記得確認這裡是你的 Render 網址！)
API_URL = "https://my-rescue-api-v1.onrender.com"

# 1. 初始化地理編碼器 (這是我們的新裝備)
geolocator = Nominatim(user_agent="e_rescue_pro_v1")

# --- 畫面外觀設定 ---
st.set_page_config(page_title="E-Rescue 生活救援", page_icon="📱", layout="centered")
st.title("🚗 E-Rescue 全方位生活救援 APP")

# 建立兩個分頁
tab_client, tab_provider = st.tabs(["🙋‍♂️ 我是客戶 (叫修)", "🦸‍♂️ 我是師傅 (接單)"])

# ==========================================
# 分頁 1：客戶端畫面 (📍 地址搜尋升級版)
# ==========================================
with tab_client:
    st.markdown("### 遇到困難了嗎？馬上呼叫專業師傅！")

    # 📍 新增：地址輸入框
    user_address = st.text_input("📍 請輸入您的救援地址或地標：", placeholder="例如：台中火車站 或 台北市信義路五段7號")

    # 初始化預設座標 (預設在台中市)
    target_lat, target_lng = 24.16, 120.68

    # 如果使用者有輸入地址，就開始執行搜尋！
    if user_address:
        with st.spinner("正在精確定位中..."):
            try:
                location = geolocator.geocode(user_address)
                if location:
                    target_lat = location.latitude
                    target_lng = location.longitude
                    st.success(f"📍 已精確定位：{location.address}")

                    # 立即在地圖上顯示座標
                    map_data = [{"lat": target_lat, "lon": target_lng}]
                    st.map(map_data, zoom=15)
                else:
                    st.warning("找不到這個地址，請嘗試輸入更完整的資訊喔！")
            except Exception as e:
                st.error(f"定位服務暫時無法連線：{e}")

    # 下方的表單 (呼叫按鈕)
    with st.form("request_form"):
        category = st.selectbox("1️⃣ 需要什麼服務？", ["機車拋錨", "水電問題", "園藝問題", "開鎖服務", "其他"])
        description = st.text_area("2️⃣ 請簡單描述狀況")

        submitted = st.form_submit_button("🚨 立即呼叫救援")

        if submitted:
            if not description:
                st.warning("請填寫狀況描述喔！")
            else:
                with st.spinner("系統正在為您媒合師傅中..."):
                    # 這裡的經緯度已經自動變成上面搜尋到的結果了！
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
                            st.success("✅ 呼叫成功！系統正在為您媒合師傅...")
                            st.balloons()
                        else:
                            st.error(f"❌ 呼叫失敗！錯誤碼：{res.status_code}")
                            st.write("大腦說：", res.text)
                    except Exception as e:
                        st.error(f"⚠️ 連線發生嚴重錯誤：{e}")

# ==========================================
# 分頁 2：師傅端畫面 (維持原樣，帶有地圖)
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

                        # 顯示客戶的地圖位置
                        map_data = [{"lat": task["req_lat"], "lon": task["req_lng"]}]
                        st.map(map_data, zoom=14)
                        st.markdown("---")

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