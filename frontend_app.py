import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
from geopy.geocoders import ArcGIS

# 🔗 連結你的雲端大腦
API_URL = "https://my-rescue-api-v1.onrender.com"
geolocator = ArcGIS()

st.set_page_config(page_title="E-Rescue 生活救援", page_icon="📱", layout="centered")

# 🧠 網頁記憶區初始化
if "user" not in st.session_state:
    st.session_state.user = None
if "role" not in st.session_state:
    st.session_state.role = None
if "order_id" not in st.session_state:
    st.session_state.order_id = None
if "order_status" not in st.session_state:
    st.session_state.order_status = "pending"
if "order_category" not in st.session_state:
    st.session_state.order_category = None

# ==========================================
# 🚨 AMBER Alert 全局緊急廣播偵測
# ==========================================
try:
    alert_res = requests.get(f"{API_URL}/alert/active")
    if alert_res.status_code == 200:
        alert_data = alert_res.json()
        if alert_data.get("active"):
            st.error(f"🚨 **【緊急協尋廣播】** {alert_data['message']}")
            st.markdown("---")
except:
    pass  # 避免 API 還沒重啟完成時報錯

st.title("🚗 E-Rescue 全方位生活救援 APP")

# ==========================================
# 🔐 側邊欄：會員登入系統 & 管理員後台
# ==========================================
with st.sidebar:
    if st.session_state.user is None:
        st.header("🔐 會員登入")
        auth_mode = st.radio("請選擇：", ["登入", "註冊新帳號"])
        username = st.text_input("帳號 (Username)")
        password = st.text_input("密碼 (Password)", type="password")

        if auth_mode == "註冊新帳號":
            role = st.selectbox("您的身分？", ["🙋‍♂️ 一般客戶 (需要救援)", "🦸‍♂️ 專業師傅 (提供救援)"])
            role_value = "client" if "客戶" in role else "provider"
        if st.button("📝 立即註冊"):
            try:
                res = requests.post(f"{API_URL}/register",
                                    json={"username": username, "password": password, "role": role_value})
                if res.status_code == 200:
                    st.success("註冊成功！請切換到「登入」進行登入。")
                else:
                    # 🛡️ 防呆：如果大腦傳回來的不是 JSON，我們就優雅地攔截它
                    try:
                        error_msg = res.json().get('detail', '未知錯誤')
                    except:
                        error_msg = f"大腦無回應 (代碼: {res.status_code})。可能是大腦還在重新開機，請等 1 分鐘後再試！"
                    st.error(f"註冊失敗：{error_msg}")
            except Exception as e:
                st.error(f"🚨 無法連線到大腦！請確認 Render 是否還在更新中。錯誤：{e}")


        else:
            if st.button("🚀 登入"):
                res = requests.post(f"{API_URL}/login", json={"username": username, "password": password})
                if res.status_code == 200:
                    data = res.json()
                    st.session_state.user = data["username"]
                    st.session_state.role = data["role"]
                    st.success("登入成功！")
                    st.rerun()
                else:
                    st.error("帳號或密碼錯誤！")
    else:
        st.success(f"👤 歡迎回來，{st.session_state.user}！")
        st.write(f"目前身分：{'一般客戶' if st.session_state.role == 'client' else '專業師傅'}")
        if st.button("🚪 登出"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

        # 👑 隱藏的 CEO 管理員後台 (只要帳號是 admin 就能看見)
        if st.session_state.user == "admin":
            st.markdown("---")
            st.header("👑 CEO 廣播台")
            alert_msg = st.text_input("發布緊急協尋：")
            if st.button("🚨 發送 AMBER Alert"):
                requests.post(f"{API_URL}/alert", json={"message": alert_msg})
                st.success("廣播已發布！所有人網頁都會看到！")
                st.rerun()

# ==========================================
# 🚀 擋修機制：沒登入不准叫車
# ==========================================

if st.session_state.user is None:
    st.info("👈 請先在左側欄位登入或註冊，才能使用 E-Rescue 服務喔！")
else:
    SERVICE_LIST = ["機車拋錨", "水電問題", "園藝問題", "開鎖服務", "📦 搬家服務", "🔎 失物協尋", "其他"]

    # 🌟 升級：新增第三個分頁「我的紀錄」
    tab_client, tab_provider, tab_history = st.tabs(["🙋‍♂️ 我是客戶 (叫修)", "🦸‍♂️ 我是師傅 (接單)", "📜 我的紀錄"])

    # --- 分頁 1：客戶端畫面 ---
    with tab_client:
        if st.session_state.order_id is None:
            user_address = st.text_input("🔍 快速搜尋地址：", placeholder="例如：台中市北區五權路277號")
            target_lat, target_lng = 24.16, 120.68

            if user_address:
                with st.spinner("定位中..."):
                    try:
                        location = geolocator.geocode(user_address)
                        if location:
                            target_lat, target_lng = location.latitude, location.longitude
                            st.success(f"📍 搜尋成功：{location.address}")
                    except:
                        pass

            m = folium.Map(location=[target_lat, target_lng], zoom_start=15)
            if user_address:
                folium.Marker([target_lat, target_lng], popup="搜尋中心").add_to(m)
            m.add_child(folium.LatLngPopup())
            map_data = st_folium(m, height=300, width=700, key="interactive_map")

            final_lat, final_lng = target_lat, target_lng
            if map_data and map_data.get("last_clicked"):
                final_lat, final_lng = map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"]

            with st.form("request_form"):
                category = st.selectbox("1️⃣ 需要什麼服務？", SERVICE_LIST)
                description = st.text_area("2️⃣ 請簡單描述狀況")
                if st.form_submit_button("🚨 立即呼叫救援"):
                    if description:
                        payload = {"description": description, "req_lng": final_lng, "req_lat": final_lat,
                                   "user_id": st.session_state.user, "category": category}
                        res = requests.post(f"{API_URL}/requests", json=payload)
                        if res.status_code == 200:
                            st.session_state.order_id = res.json().get("request_id")
                            st.session_state.order_status = "pending"
                            st.session_state.order_category = category
                            st.rerun()

        else:
            st.markdown("### 🚁 救援小組派遣中...")
            if st.session_state.order_status == "pending":
                st.warning("⏳ 正在等待附近的專業師傅接單...")
                st.progress(30)
            elif st.session_state.order_status == "accepted":
                st.success("🎉 熱血師傅已接單！正在火速趕往您的位置！")
                st.progress(100)

            col1, col2 = st.columns(2)
            if col1.button("🔄 檢查最新狀態"):
                check_res = requests.get(f"{API_URL}/provider/requests",
                                         params={"category": st.session_state.order_category})
                if check_res.status_code == 200:
                    if st.session_state.order_id not in [t["request_id"] for t in check_res.json()]:
                        st.session_state.order_status = "accepted"
                        st.rerun()
                        # 💡 客戶可以隨時清除目前畫面，準備叫下一波救援
            if col2.button("❌ 關閉此畫面 / 叫新救援"):
                st.session_state.order_id = None
                st.session_state.order_status = "pending"
                st.rerun()

    # --- 分頁 2：師傅端畫面 ---
    with tab_provider:
        st.markdown("### 📋 專屬任務牆")
        my_skill = st.selectbox("請選擇您的專業領域：", SERVICE_LIST)
        st.button("🔄 刷新任務牆")

        try:
            res = requests.get(f"{API_URL}/provider/requests", params={"category": my_skill})
            if res.status_code == 200:
                tasks = res.json()
                if len(tasks) == 0:
                    st.warning("目前沒有待處理訂單。")
                else:
                    st.success(f"發現 {len(tasks)} 筆新任務！")
                    for task in tasks:
                        with st.container():
                            st.markdown("---")
                            st.markdown(f"**👤 客戶：** `{task['user_id']}`")
                            st.markdown(f"**📝 狀況：** {task['description']}")

                            m_provider = folium.Map(location=[task["req_lat"], task["req_lng"]], zoom_start=16)
                            folium.Marker([task["req_lat"], task["req_lng"]],
                                          icon=folium.Icon(color="red", icon="info-sign")).add_to(m_provider)
                            st_folium(m_provider, height=250, width=700, key=f"map_prov_{task['request_id']}")

                            if st.button(f"✅ 點我接單！", key=f"btn_accept_{task['request_id']}"):
                                requests.put(f"{API_URL}/provider/requests/{task['request_id']}/accept",
                                             params={"provider_id": st.session_state.user})
                                st.success("🎉 接單成功！請盡速前往救援，完成後可至「我的紀錄」結案。")
        except:
            pass

    # --- 分頁 3：📜 歷史紀錄與結案區 (全新功能！) ---
    with tab_history:
        st.markdown(f"### 📂 {st.session_state.user} 的專屬紀錄")
        if st.button("🔄 刷新紀錄"):
            pass  # 按下後會自動重跑下方的 API 請求

        try:
            history_res = requests.get(f"{API_URL}/users/{st.session_state.user}/history",
                                       params={"role": st.session_state.role})
            if history_res.status_code == 200:
                history_tasks = history_res.json()

                if not history_tasks:
                    st.info("目前還沒有任何紀錄喔！")
                else:
                    for task in history_tasks:
                        with st.expander(
                                f"📦 [{task['status'].upper()}] {task['category']} - {task['description'][:10]}..."):
                            st.write(f"**訂單編號：** `{task['request_id']}`")
                            st.write(f"**詳細狀況：** {task['description']}")

                            if st.session_state.role == "client":
                                st.write(f"**負責師傅：** {task.get('provider_id', '尚未接單')}")
                            else:
                                st.write(f"**發案客戶：** {task['user_id']}")

                            # 🏁 師傅專屬的結案按鈕
                            if st.session_state.role == "provider" and task['status'] == 'accepted':
                                if st.button("✅ 救援完成 (點擊結案)", key=f"btn_complete_{task['request_id']}"):
                                    complete_res = requests.put(f"{API_URL}/requests/{task['request_id']}/complete")
                                    if complete_res.status_code == 200:
                                        st.success("任務圓滿達成！辛苦了！")
                                        st.rerun()
            else:
                st.error("無法取得歷史紀錄。")
        except Exception as e:
            st.error(f"連線錯誤：{e}")