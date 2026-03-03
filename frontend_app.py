import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
from geopy.geocoders import ArcGIS

API_URL = "https://my-rescue-api-v1.onrender.com"
geolocator = ArcGIS()

st.set_page_config(page_title="E-Rescue 生活救援", page_icon="📱", layout="centered")
st.title("🚗 E-Rescue 全方位生活救援 APP")

# 🧠 給網頁加上「記憶力」
if "order_id" not in st.session_state:
    st.session_state.order_id = None
if "order_status" not in st.session_state:
    st.session_state.order_status = "pending"
# 💡 新增：記住訂單的分類，這樣才能正確去任務牆對答案！
if "order_category" not in st.session_state:
    st.session_state.order_category = None

tab_client, tab_provider = st.tabs(["🙋‍♂️ 我是客戶 (叫修)", "🦸‍♂️ 我是師傅 (接單)"])

# ==========================================
# 分頁 1：客戶端畫面 (搜尋 + 點擊 雙刀流)
# ==========================================
with tab_client:
    if st.session_state.order_id is None:
        st.markdown("### 📍 步驟 1：鎖定您的救援位置")

        user_address = st.text_input("🔍 快速搜尋地址 (搜尋後會移動地圖)：", placeholder="例如：台中市北區五權路277號")
        target_lat, target_lng = 24.16, 120.68

        if user_address:
            with st.spinner("正在搜尋地址..."):
                try:
                    location = geolocator.geocode(user_address)
                    if location:
                        target_lat = location.latitude
                        target_lng = location.longitude
                        st.success(f"📍 搜尋成功：{location.address}")
                    else:
                        st.warning("找不到此地址，請嘗試直接點擊下方地圖。")
                except:
                    st.error("定位服務暫時無回應")

        st.info("💡 您可以直接在地圖上「點擊」來精確指定您拋錨的路口！")
        m = folium.Map(location=[target_lat, target_lng], zoom_start=15)

        if user_address:
            folium.Marker([target_lat, target_lng], popup="搜尋中心", tooltip="搜尋中心").add_to(m)

        m.add_child(folium.LatLngPopup())

        map_data = st_folium(m, height=350, width=700, key="interactive_map")

        final_lat, final_lng = target_lat, target_lng

        if map_data and map_data.get("last_clicked"):
            final_lat = map_data["last_clicked"]["lat"]
            final_lng = map_data["last_clicked"]["lng"]
            st.success(f"✅ 已鎖定「地圖點擊」位置：緯度 {final_lat:.4f}, 經度 {final_lng:.4f}")
        elif user_address:
            st.success(f"✅ 已鎖定「地址搜尋」位置：緯度 {final_lat:.4f}, 經度 {final_lng:.4f}")

        with st.form("request_form"):
            category = st.selectbox("1️⃣ 需要什麼服務？",
                                    ["機車拋錨", "水電問題", "園藝問題", "開鎖服務", "搬家服務", "失物協尋", "其他"])
            description = st.text_area("2️⃣ 請簡單描述狀況")
            submitted = st.form_submit_button("🚨 立即呼叫救援")

            if submitted:
                if not description:
                    st.warning("請填寫狀況描述喔！")
                else:
                    with st.spinner("系統正在發送訂單..."):
                        payload = {
                            "description": description,
                            "req_lng": final_lng,
                            "req_lat": final_lat,
                            "user_id": "VIP客戶_001",
                            "category": category
                        }
                        try:
                            res = requests.post(f"{API_URL}/requests", json=payload)
                            if res.status_code == 200:
                                data = res.json()
                                st.session_state.order_id = data.get("request_id")
                                st.session_state.order_status = "pending"
                                # 💡 記住這個分類！
                                st.session_state.order_category = category
                                st.rerun()
                            else:
                                st.error("❌ 呼叫失敗！")
                        except Exception as e:
                            st.error(f"連線錯誤：{e}")

    else:
        st.markdown("### 🚁 救援小組派遣中...")
        st.write(f"**您的專屬訂單編號：** `{st.session_state.order_id[:8]}...`")

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
                        # 💡 帶上 order_category 參數，API 就不會報錯了！
                        check_res = requests.get(f"{API_URL}/provider/requests",
                                                 params={"category": st.session_state.order_category})
                        if check_res.status_code == 200:
                            pending_tasks = check_res.json()
                            pending_ids = [task["request_id"] for task in pending_tasks]

                            if st.session_state.order_id not in pending_ids:
                                st.session_state.order_status = "accepted"
                                st.rerun()
                            else:
                                st.toast("👀 師傅還在路上，請再稍等一下喔！")
                        else:
                            st.error(f"API 回傳錯誤碼：{check_res.status_code}")
                    except Exception as e:
                        st.error(f"查詢失敗：{e}")

        with col2:
            if st.button("❌ 完成救援 / 重新呼叫"):
                st.session_state.order_id = None
                st.session_state.order_status = "pending"
                st.session_state.order_category = None
                st.rerun()

# ==========================================
# 分頁 2：師傅端畫面 (🗺️ 彩色地圖升級版)
# ==========================================
with tab_provider:
    st.markdown("### 📋 專屬任務牆")
    st.info("系統會自動幫您過濾出符合您專業，且尚未被接走的訂單。")

    my_skill = st.selectbox("請選擇您的專業領域：", ["機車拋錨", "水電問題", "園藝問題", "開鎖服務","搬家服務", "失物協尋", "其他"])
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

                        # 🗺️ 升級：改用 Folium 畫出彩色的專業地圖！
                        m_provider = folium.Map(location=[task["req_lat"], task["req_lng"]], zoom_start=16)
                        # 加一個大紅色的標記，讓師傅一眼看出地點
                        folium.Marker(
                            [task["req_lat"], task["req_lng"]],
                            popup="救援地點",
                            icon=folium.Icon(color="red", icon="info-sign")
                        ).add_to(m_provider)

                        st_folium(m_provider, height=250, width=700, key=f"map_provider_{task['request_id']}")

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