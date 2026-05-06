import streamlit as st
import requests
import base64
import json
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from PIL import Image
import io
from datetime import datetime, timedelta
import os
import glob

# ==================== 页面配置 ====================
# AI辅助生成：DeepSeek，2026-04-10，用于Streamlit页面基础配置代码模板
st.set_page_config(
    page_title="食析智导 -基于 DRIs 标准的地域化膳食系统",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==================== 百度API配置 ====================
# AI辅助生成：DeepSeek，2026-04-10，用于百度菜品识别API调用框架
API_KEY = "GJUPu98MpBdmASRiADbwaSrO"
SECRET_KEY = "S7wpGU9mE6hAMoiBeK1WFp6ZZ0OL1mmZ"

DISH_RECOGNIZE_URL = "https://aip.baidubce.com/rest/2.0/image-classify/v2/dish"

# ==================== 本地存储配置 ====================
# AI辅助生成：DeepSeek，2026-04-11，用于本地JSON数据持久化存储函数模板
DATA_DIR = "nutrition_data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


def get_week_key(date=None):
    """获取当前周的标识符（周一日期）"""
    if date is None:
        date = datetime.now()
    monday = date - timedelta(days=date.weekday())
    return monday.strftime("%Y-%m-%d")


def get_today_key():
    """获取今天的日期标识符"""
    return datetime.now().strftime("%Y-%m-%d")


def get_day_of_week():
    """获取今天是周几"""
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    return weekdays[datetime.now().weekday()]


def load_week_data(week_key=None):
    """加载指定周的数据"""
    if week_key is None:
        week_key = get_week_key()

    file_path = os.path.join(DATA_DIR, f"week_{week_key}.json")

    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_week_data(week_data, week_key=None):
    """保存周数据"""
    if week_key is None:
        week_key = get_week_key()

    file_path = os.path.join(DATA_DIR, f"week_{week_key}.json")

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(week_data, f, ensure_ascii=False, indent=2)


def save_today_dishes(dish_list):
    """保存今日的菜品记录"""
    week_key = get_week_key()
    today_key = get_today_key()

    week_data = load_week_data(week_key)
    week_data[today_key] = {
        "dishes": dish_list,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    save_week_data(week_data, week_key)
    cleanup_old_data(keep_weeks=4)


def load_today_dishes():
    """加载今日的菜品记录"""
    week_key = get_week_key()
    today_key = get_today_key()
    week_data = load_week_data(week_key)

    if today_key in week_data:
        return week_data[today_key].get("dishes", [])
    return []


def get_week_summary(week_key=None):
    """获取周汇总数据"""
    if week_key is None:
        week_key = get_week_key()

    week_data = load_week_data(week_key)

    summary = {
        "week_key": week_key,
        "days_recorded": 0,
        "total_calories": 0,
        "daily_calories": {},
        "all_dishes": []
    }

    for date_key, day_data in week_data.items():
        if "dishes" in day_data:
            dishes = day_data["dishes"]
            day_calories = sum(d.get("calorie", 0) for d in dishes)

            summary["days_recorded"] += 1
            summary["total_calories"] += day_calories
            summary["daily_calories"][date_key] = day_calories
            summary["all_dishes"].extend(dishes)

    return summary


def get_available_weeks():
    """获取所有可用的周数据"""
    weeks = []
    pattern = os.path.join(DATA_DIR, "week_*.json")

    for file_path in glob.glob(pattern):
        filename = os.path.basename(file_path)
        week_key = filename.replace("week_", "").replace(".json", "")
        weeks.append(week_key)

    weeks.sort(reverse=True)
    return weeks


def cleanup_old_data(keep_weeks=4):
    """清理旧数据，只保留最近N周"""
    weeks = get_available_weeks()

    if len(weeks) > keep_weeks:
        for week_key in weeks[keep_weeks:]:
            file_path = os.path.join(DATA_DIR, f"week_{week_key}.json")
            try:
                os.remove(file_path)
            except:
                pass


@st.cache_data(ttl=3600)
def get_access_token():
    """获取百度API access_token"""
    # AI辅助生成：DeepSeek，2026-04-12，用于百度API鉴权token获取代码模板
    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {
        "grant_type": "client_credentials",
        "client_id": API_KEY,
        "client_secret": SECRET_KEY
    }
    try:
        response = requests.post(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json().get("access_token")
        else:
            return None
    except:
        return None


def recognize_dish(image_bytes):
    """调用百度菜品识别API"""
    # AI辅助生成：百度文心系列，2026-04-12，用于百度菜品识别API调用
    access_token = get_access_token()
    if not access_token:
        return None

    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    url = f"{DISH_RECOGNIZE_URL}?access_token={access_token}"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {"image": image_base64, "top_num": 3, "baike_num": 0}

    try:
        response = requests.post(url, headers=headers, data=data, timeout=30)
        if response.status_code == 200:
            result = response.json()
            if "result" in result and len(result["result"]) > 0:
                return result["result"]
        return None
    except:
        return None


# ==================== BMI计算 ====================
# AI辅助生成：DeepSeek，2026-04-13，用于BMI计算与分类逻辑代码模板
def calculate_bmi(weight, height_cm):
    height_m = height_cm / 100
    bmi = weight / (height_m ** 2)
    return round(bmi, 1)


def get_bmi_category(bmi, age):
    if age >= 80:
        if bmi < 22:
            return "体重过低", "建议适当增加营养，维持健康体重"
        elif bmi <= 26.9:
            return "体重正常", "继续保持健康生活方式"
        else:
            return "超重", "建议在医生指导下科学减重"
    else:
        if bmi < 18.5:
            return "体重过低", "建议增加营养摄入，适度增肌"
        elif bmi < 24:
            return "体重正常", "保持均衡饮食和适量运动"
        elif bmi < 28:
            return "超重", "建议控制饮食，加强运动"
        else:
            return "肥胖", "建议科学减重，遵循卫健委指南"


def get_daily_calorie_target(weight, height_cm, age, gender, goal, activity_level="轻度"):
    # AI辅助生成：DeepSeek，2026-04-13，用于每日热量目标计算逻辑
    if gender == "男":
        bmr = 10 * weight + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height_cm - 5 * age - 161

    activity_factors = {"久坐": 1.2, "轻度": 1.375, "中度": 1.55, "高度": 1.725}
    tdee = bmr * activity_factors.get(activity_level, 1.375)

    if goal == "减重":
        daily_target = tdee - 500
        min_cal = 1200 if gender == "男" else 1000
        daily_target = max(daily_target, min_cal)
    elif goal == "增肌":
        daily_target = tdee + 300
    else:
        daily_target = tdee

    return round(daily_target)


# ==================== 营养素标准 ====================
NUTRIENT_STANDARDS = {
    "热量": {"男": 2250, "女": 1800, "单位": "kcal"},
    "蛋白质": {"男": 65, "女": 55, "单位": "g"},
    "脂肪": {"男": 60, "女": 50, "单位": "g"},
    "碳水": {"男": 300, "女": 260, "单位": "g"},
    "膳食纤维": {"男": 30, "女": 25, "单位": "g"},
    "钙": {"男": 800, "女": 800, "单位": "mg"},
    "铁": {"男": 12, "女": 20, "单位": "mg"},
    "锌": {"男": 12.5, "女": 7.5, "单位": "mg"},
    "维生素A": {"男": 800, "女": 700, "单位": "μg"},
    "维生素C": {"男": 100, "女": 100, "单位": "mg"},
    "维生素D": {"男": 10, "女": 10, "单位": "μg"},
    "维生素E": {"男": 14, "女": 14, "单位": "mg"},
}

# 地域食物推荐
REGION_FOOD_RECOMMENDATIONS = {
    "碳水": {
        "东北": ["大米饭", "玉米饼", "粘豆包", "高粱米饭"],
        "华北": ["馒头", "面条", "烙饼", "饺子", "包子"],
        "华东": ["米饭", "年糕", "汤圆", "小笼包"],
        "华中": ["米饭", "热干面", "米粉", "糍粑"],
        "华南": ["米饭", "肠粉", "河粉", "米粉"],
        "西南": ["米饭", "米线", "饵块", "抄手"],
        "西北": ["面条", "馍", "馕", "拉条子"]
    },
    "蛋白质": {
        "东北": ["锅包肉", "小鸡炖蘑菇", "酱大骨"],
        "华北": ["烤鸭", "涮羊肉", "酱牛肉"],
        "华东": ["红烧肉", "清蒸鱼", "盐水鸭"],
        "华中": ["剁椒鱼头", "腊肉", "武昌鱼"],
        "华南": ["白切鸡", "烧鹅", "海鲜"],
        "西南": ["水煮鱼", "回锅肉", "火锅"],
        "西北": ["手抓羊肉", "烤羊肉串", "大盘鸡"]
    },
    "膳食纤维": {
        "东北": ["酸菜", "木耳", "大白菜"],
        "华北": ["大白菜", "菠菜", "韭菜", "芹菜"],
        "华东": ["青菜", "芹菜", "莲藕", "竹笋"],
        "华中": ["莲藕", "萝卜", "白菜"],
        "华南": ["空心菜", "芥蓝", "菜心"],
        "西南": ["折耳根", "豌豆尖", "竹笋"],
        "西北": ["土豆", "萝卜", "白菜"]
    },
    "钙": {
        "东北": ["牛奶", "酸奶", "豆腐"],
        "华北": ["牛奶", "酸奶", "豆腐", "虾皮"],
        "华东": ["牛奶", "小油菜", "豆腐"],
        "华中": ["牛奶", "豆腐", "小鱼干"],
        "华南": ["牛奶", "豆腐", "海带", "虾皮"],
        "西南": ["牛奶", "豆花", "虾皮"],
        "西北": ["牛奶", "酸奶", "奶酪"]
    },
    "铁": {
        "东北": ["猪血肠", "菠菜", "黑木耳"],
        "华北": ["猪肝", "菠菜", "红枣"],
        "华东": ["鸭血", "猪肝", "菠菜"],
        "华中": ["猪血", "菠菜", "黑木耳"],
        "华南": ["猪肝", "菠菜", "红肉"],
        "西南": ["猪血旺", "菠菜", "黑木耳"],
        "西北": ["羊肉", "红枣", "菠菜"]
    },
    "维生素C": {
        "东北": ["青椒", "西红柿", "白菜"],
        "华北": ["青椒", "西红柿", "猕猴桃"],
        "华东": ["青椒", "西红柿", "柑橘"],
        "华中": ["青椒", "橙子", "猕猴桃"],
        "华南": ["青椒", "橙子", "柚子"],
        "西南": ["青椒", "橙子", "猕猴桃"],
        "西北": ["青椒", "西红柿", "沙棘"]
    }
}

GENERAL_FOOD_SUGGESTIONS = {
    "热量": ["全谷物", "薯类", "坚果"],
    "蛋白质": ["鸡胸肉", "鱼虾", "鸡蛋", "豆制品", "牛奶"],
    "脂肪": ["坚果", "牛油果", "橄榄油"],
    "碳水": ["全麦面包", "燕麦", "糙米", "红薯"],
    "膳食纤维": ["绿叶蔬菜", "水果", "全谷物"],
    "钙": ["牛奶", "酸奶", "豆腐", "芝麻"],
    "铁": ["红肉", "动物肝脏", "菠菜", "红枣"],
    "锌": ["生蚝", "瘦肉", "坚果", "蛋黄"],
    "维生素A": ["胡萝卜", "南瓜", "菠菜", "红薯"],
    "维生素C": ["橙子", "猕猴桃", "青椒", "西红柿"],
    "维生素D": ["鱼肝油", "三文鱼", "蛋黄"],
    "维生素E": ["坚果", "植物油", "菠菜"]
}

DISH_NUTRITION_DB = {
    "炒牛肉": {"热量": 120, "蛋白质": 22.0, "脂肪": 3.5, "碳水": 2.0, "膳食纤维": 0.5, "钙": 10, "铁": 3.5, "锌": 5.0,
               "维生素A": 0, "维生素C": 0, "维生素D": 0.2, "维生素E": 0.5},
    "牛肉": {"热量": 125, "蛋白质": 20.0, "脂肪": 4.0, "碳水": 2.0, "膳食纤维": 0, "钙": 12, "铁": 3.0, "锌": 4.5,
             "维生素A": 0, "维生素C": 0, "维生素D": 0.2, "维生素E": 0.4},
    "鸡胸肉": {"热量": 133, "蛋白质": 23.5, "脂肪": 4.2, "碳水": 0, "膳食纤维": 0, "钙": 12, "铁": 1.1, "锌": 0.8,
               "维生素A": 15, "维生素C": 0, "维生素D": 0.2, "维生素E": 0.3},
    "鸡肉": {"热量": 167, "蛋白质": 19.3, "脂肪": 9.4, "碳水": 1.3, "膳食纤维": 0, "钙": 11, "铁": 1.3, "锌": 1.0,
             "维生素A": 48, "维生素C": 2, "维生素D": 0.2, "维生素E": 0.3},
    "红烧肉": {"热量": 520, "蛋白质": 8.2, "脂肪": 52.3, "碳水": 2.8, "膳食纤维": 0, "钙": 6, "铁": 1.6, "锌": 1.2,
               "维生素A": 10, "维生素C": 0, "维生素D": 0.5, "维生素E": 0.5},
    "猪肉": {"热量": 395, "蛋白质": 13.2, "脂肪": 37.0, "碳水": 2.4, "膳食纤维": 0, "钙": 6, "铁": 1.6, "锌": 2.0,
             "维生素A": 10, "维生素C": 0, "维生素D": 0.5, "维生素E": 0.5},
    "米饭": {"热量": 116, "蛋白质": 2.6, "脂肪": 0.3, "碳水": 25.6, "膳食纤维": 0.3, "钙": 7, "铁": 1.3, "锌": 0.9,
             "维生素A": 0, "维生素C": 0, "维生素D": 0, "维生素E": 0},
    "面条": {"热量": 284, "蛋白质": 8.3, "脂肪": 1.1, "碳水": 61.9, "膳食纤维": 1.5, "钙": 13, "铁": 2.5, "锌": 0.8,
             "维生素A": 0, "维生素C": 0, "维生素D": 0, "维生素E": 0.2},
    "饺子": {"热量": 240, "蛋白质": 8.5, "脂肪": 9.2, "碳水": 30.5, "膳食纤维": 1.2, "钙": 35, "铁": 1.5, "锌": 0.7,
             "维生素A": 30, "维生素C": 2, "维生素D": 0.1, "维生素E": 0.4},
    "馒头": {"热量": 223, "蛋白质": 7.0, "脂肪": 1.1, "碳水": 47.0, "膳食纤维": 1.3, "钙": 18, "铁": 1.8, "锌": 0.6,
             "维生素A": 0, "维生素C": 0, "维生素D": 0, "维生素E": 0.1},
    "青菜": {"热量": 25, "蛋白质": 1.8, "脂肪": 0.3, "碳水": 3.8, "膳食纤维": 1.6, "钙": 90, "铁": 1.2, "锌": 0.4,
             "维生素A": 280, "维生素C": 36, "维生素D": 0, "维生素E": 0.8},
    "西红柿炒鸡蛋": {"热量": 145, "蛋白质": 6.2, "脂肪": 10.5, "碳水": 6.8, "膳食纤维": 1.2, "钙": 48, "铁": 1.8,
                     "锌": 0.8, "维生素A": 350, "维生素C": 12, "维生素D": 0.8, "维生素E": 1.2},
    "番茄炒蛋": {"热量": 145, "蛋白质": 6.2, "脂肪": 10.5, "碳水": 6.8, "膳食纤维": 1.2, "钙": 48, "铁": 1.8, "锌": 0.8,
                 "维生素A": 350, "维生素C": 12, "维生素D": 0.8, "维生素E": 1.2},
    "西兰花": {"热量": 36, "蛋白质": 4.1, "脂肪": 0.6, "碳水": 4.3, "膳食纤维": 2.6, "钙": 67, "铁": 1.0, "锌": 0.4,
               "维生素A": 120, "维生素C": 89, "维生素D": 0, "维生素E": 0.8},
    "清蒸鱼": {"热量": 105, "蛋白质": 18.5, "脂肪": 3.2, "碳水": 0, "膳食纤维": 0, "钙": 38, "铁": 0.8, "锌": 1.1,
               "维生素A": 15, "维生素C": 0, "维生素D": 5, "维生素E": 0.8},
    "鱼": {"热量": 105, "蛋白质": 18.5, "脂肪": 3.2, "碳水": 0, "膳食纤维": 0, "钙": 38, "铁": 0.8, "锌": 1.1,
           "维生素A": 15, "维生素C": 0, "维生素D": 5, "维生素E": 0.8},
    "虾": {"热量": 93, "蛋白质": 18.6, "脂肪": 1.5, "碳水": 1.0, "膳食纤维": 0, "钙": 62, "铁": 1.5, "锌": 2.0,
           "维生素A": 15, "维生素C": 0, "维生素D": 1.0, "维生素E": 1.0},
    "鸡蛋": {"热量": 144, "蛋白质": 13.3, "脂肪": 9.8, "碳水": 1.4, "膳食纤维": 0, "钙": 56, "铁": 2.0, "锌": 1.3,
             "维生素A": 234, "维生素C": 0, "维生素D": 2.0, "维生素E": 1.2},
    "牛奶": {"热量": 54, "蛋白质": 3.0, "脂肪": 3.2, "碳水": 3.4, "膳食纤维": 0, "钙": 104, "铁": 0.3, "锌": 0.4,
             "维生素A": 24, "维生素C": 0, "维生素D": 1.0, "维生素E": 0.1},
    "豆腐": {"热量": 81, "蛋白质": 8.1, "脂肪": 3.7, "碳水": 4.2, "膳食纤维": 0.4, "钙": 164, "铁": 1.9, "锌": 0.6,
             "维生素A": 0, "维生素C": 0, "维生素D": 0, "维生素E": 0.1},
}

DEFAULT_NUTRITION = {"热量": 100, "蛋白质": 5.0, "脂肪": 3.0, "碳水": 10.0, "膳食纤维": 1.0, "钙": 20, "铁": 0.5,
                     "锌": 0.3, "维生素A": 20, "维生素C": 5, "维生素D": 0, "维生素E": 0.2}


def get_region_foods(nutrient, region):
    if nutrient in REGION_FOOD_RECOMMENDATIONS and region in REGION_FOOD_RECOMMENDATIONS[nutrient]:
        return REGION_FOOD_RECOMMENDATIONS[nutrient][region]
    return GENERAL_FOOD_SUGGESTIONS.get(nutrient, ["各类食物"])


def find_matching_dish(dish_name):
    if not dish_name:
        return None
    if dish_name in DISH_NUTRITION_DB:
        return dish_name
    for key in DISH_NUTRITION_DB:
        if key in dish_name or dish_name in key:
            return key
    return None


# ==================== 初始化 Session State ====================
# AI辅助生成：DeepSeek，2026-04-14，用于Streamlit会话状态初始化与管理模板
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'profile_completed' not in st.session_state:
    st.session_state['profile_completed'] = False
if 'dish_list' not in st.session_state:
    st.session_state['dish_list'] = []
if 'current_dish_result' not in st.session_state:
    st.session_state['current_dish_result'] = None
if 'current_dish_name' not in st.session_state:
    st.session_state['current_dish_name'] = None
if 'current_dish_calorie' not in st.session_state:
    st.session_state['current_dish_calorie'] = 0
if 'recognition_results' not in st.session_state:
    st.session_state['recognition_results'] = []

# 用户档案
if 'user_profile' not in st.session_state:
    st.session_state['user_profile'] = {
        'age': 30,
        'gender': '男',
        'region': '华北',
        'height': 170,
        'weight': 70,
        'goal': '减重',
        'activity_level': '轻度'
    }


def add_dish_to_list(portion):
    if st.session_state['current_dish_result'] is not None:
        dish_name = st.session_state['current_dish_name']
        dish_calorie = st.session_state['current_dish_calorie']

        try:
            calorie_value = float(dish_calorie) if isinstance(dish_calorie, str) else dish_calorie
        except:
            calorie_value = 0

        actual_calorie = calorie_value * portion / 100

        st.session_state['dish_list'].append({
            "name": dish_name,
            "portion": portion,
            "calorie": actual_calorie,
            "time": datetime.now().strftime("%H:%M")
        })

        save_today_dishes(st.session_state['dish_list'])
        return True
    return False


# ==================== 登录页面 ====================
def login_page():
    st.markdown("<br><br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("""
        <div style='text-align: center; padding: 40px 20px; background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%); border-radius: 20px; margin-bottom: 30px;'>
            <h1 style='color: white; margin: 0;'>🥗 食析智导 -基于 DRIs 标准的地域化膳食系统</h1>
            <p style='color: rgba(255,255,255,0.9); margin-top: 10px;'>基于AI菜品识别 + 卫健委指南</p>
        </div>
        """, unsafe_allow_html=True)

        with st.container():
            st.markdown("### 🔐 登录")

            username = st.text_input("用户名", placeholder="请输入用户名", key="login_username")
            password = st.text_input("密码", type="password", placeholder="请输入密码", key="login_password")

            col_btn1, col_btn2 = st.columns([1, 1])
            with col_btn1:
                if st.button("🚪 登录", type="primary", use_container_width=True):
                    if username == "admin" and password == "admin":
                        st.session_state['logged_in'] = True
                        st.success("登录成功！")
                        st.rerun()
                    else:
                        st.error("用户名或密码错误")
            with col_btn2:
                if st.button("🔄 重置", use_container_width=True):
                    st.rerun()

            st.markdown("---")
            st.markdown("""
            <div style='text-align: center; color: gray; font-size: 14px;'>
            默认账号: admin / admin<br>
            </div>
            """, unsafe_allow_html=True)


# ==================== 个人档案页面 ====================
def profile_page():
    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("""
        <div style='text-align: center; padding: 30px 20px; background: linear-gradient(135deg, #2E86AB 0%, #A23B72 100%); border-radius: 20px; margin-bottom: 30px;'>
            <h1 style='color: white; margin: 0;'>📋 个人档案</h1>
            <p style='color: rgba(255,255,255,0.9); margin-top: 10px;'>请填写您的基本信息，我们将为您定制健康方案</p>
        </div>
        """, unsafe_allow_html=True)

        with st.container():
            st.markdown("### 基本信息")

            col_a, col_b = st.columns(2)
            with col_a:
                age = st.number_input("年龄", min_value=1, max_value=120, value=st.session_state['user_profile']['age'],
                                      step=1)
                gender = st.selectbox("性别", ["男", "女"],
                                      index=0 if st.session_state['user_profile']['gender'] == "男" else 1)
                region = st.selectbox("地域", ["东北", "华北", "华东", "华中", "华南", "西南", "西北"],
                                      index=["东北", "华北", "华东", "华中", "华南", "西南", "西北"].index(
                                          st.session_state['user_profile']['region']))

            with col_b:
                height = st.number_input("身高 (cm)", min_value=100, max_value=250,
                                         value=st.session_state['user_profile']['height'], step=1)
                weight = st.number_input("体重 (kg)", min_value=30, max_value=200,
                                         value=st.session_state['user_profile']['weight'], step=1)
                goal = st.selectbox("目标", ["减重", "维持", "增肌"],
                                    index=["减重", "维持", "增肌"].index(st.session_state['user_profile']['goal']))

            activity_level = st.selectbox("活动水平", ["久坐", "轻度", "中度", "高度"],
                                          index=["久坐", "轻度", "中度", "高度"].index(
                                              st.session_state['user_profile']['activity_level']))

            st.markdown("---")

            # 预览BMI
            bmi = calculate_bmi(weight, height)
            category, advice = get_bmi_category(bmi, age)
            daily_calorie_target = get_daily_calorie_target(weight, height, age, gender, goal, activity_level)

            st.markdown("### 📊 健康预览")

            col_c, col_d, col_e = st.columns(3)
            with col_c:
                st.metric("BMI", f"{bmi}")
            with col_d:
                st.metric("分类", category)
            with col_e:
                st.metric("目标热量", f"{daily_calorie_target} kcal")

            st.info(f"💡 {advice}")

            # 地域特色
            region_features = {
                "东北": "米面兼顾，炖菜为主，口味偏咸",
                "华北": "面食为主，杂粮丰富，口味适中",
                "华东": "米食为主，水产丰富，口味偏甜",
                "华中": "米食为主，辣味适中，蒸菜见长",
                "华南": "米食为主，海鲜丰富，口味清淡",
                "西南": "米食为主，麻辣鲜香，火锅盛行",
                "西北": "面食为主，牛羊肉多，口味偏咸"
            }
            st.markdown(f"**📍 {region}饮食特色**: {region_features.get(region, '')}")

            st.markdown("---")

            col_btn1, col_btn2 = st.columns([1, 1])
            with col_btn1:
                if st.button("✅ 保存并进入", type="primary", use_container_width=True):
                    st.session_state['user_profile'] = {
                        'age': age,
                        'gender': gender,
                        'region': region,
                        'height': height,
                        'weight': weight,
                        'goal': goal,
                        'activity_level': activity_level
                    }
                    st.session_state['profile_completed'] = True

                    # 加载今日数据
                    st.session_state['dish_list'] = load_today_dishes()

                    st.success("档案保存成功！")
                    st.rerun()
            with col_btn2:
                if st.button("🚪 退出登录", use_container_width=True):
                    st.session_state['logged_in'] = False
                    st.session_state['profile_completed'] = False
                    st.rerun()


# ==================== 主功能页面 ====================
def main_app():
    profile = st.session_state['user_profile']

    # 计算BMI和热量目标
    bmi = calculate_bmi(profile['weight'], profile['height'])
    category, advice = get_bmi_category(bmi, profile['age'])
    daily_calorie_target = get_daily_calorie_target(
        profile['weight'], profile['height'], profile['age'],
        profile['gender'], profile['goal'], profile['activity_level']
    )

    # 标题
    st.title("🥗 食析智导 -基于 DRIs 标准的地域化膳食系统")
    st.markdown("*基于百度AI菜品识别 + 卫健委体重管理指南*")

    col_date, col_week = st.columns(2)
    with col_date:
        st.markdown(f"📅 **{datetime.now().strftime('%Y年%m月%d日')}** {get_day_of_week()}")
    with col_week:
        week_key = get_week_key()
        st.markdown(f"📆 **第{week_key}周** (周一起)")

    st.markdown("---")

    # 侧边栏 - 显示用户信息摘要
    with st.sidebar:
        st.header(f"👤 {profile['gender']} · {profile['age']}岁")
        st.markdown(f"📍 {profile['region']} · {profile['goal']}")
        st.markdown("---")

        st.subheader("📊 BMI分析")
        st.metric("BMI", f"{bmi}")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("分类", category)
        with col2:
            st.metric("目标热量", f"{daily_calorie_target}kcal")
        st.info(f"💡 {advice}")

        st.markdown("---")

        if st.button("✏️ 修改档案", use_container_width=True):
            st.session_state['profile_completed'] = False
            st.rerun()

        if st.button("🚪 退出登录", use_container_width=True):
            st.session_state['logged_in'] = False
            st.session_state['profile_completed'] = False
            st.rerun()

    # 主界面Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📸 拍照识别", "📊 营养分析", "📝 本周报告", "📅 历史周报"])

    # ==================== Tab1: 拍照识别 ====================
    with tab1:
        st.header("📸 拍照识别菜品")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("选择图片来源")

            # 使用 radio 选择方式
            input_method = st.radio(
                "请选择图片来源",
                ["📷 拍照", "📁 上传图片"],
                horizontal=True,
                index=0,  # 默认选中拍照
                label_visibility="collapsed"
            )

            st.markdown("---")

            image_source = None

            if input_method == "📷 拍照":
                st.markdown("#### 📷 拍照")

                # 使用 session_state 控制摄像头是否显示
                if 'show_camera' not in st.session_state:
                    st.session_state['show_camera'] = False

                # 打开摄像头的按钮
                if not st.session_state['show_camera']:
                    if st.button("📷 打开摄像头", type="primary", use_container_width=True):
                        st.session_state['show_camera'] = True
                        st.rerun()

                # 显示摄像头
                if st.session_state['show_camera']:
                    camera_image = st.camera_input("点击下方按钮拍照", key="camera", label_visibility="collapsed")

                    col_cam1, col_cam2 = st.columns(2)
                    with col_cam1:
                        if st.button("📸 拍照完成", use_container_width=True):
                            if camera_image:
                                image_source = camera_image
                                st.session_state['show_camera'] = False
                                st.session_state['captured_image'] = camera_image
                                st.rerun()
                            else:
                                st.warning("请先拍照")
                    with col_cam2:
                        if st.button("❌ 关闭摄像头", use_container_width=True):
                            st.session_state['show_camera'] = False
                            st.rerun()

                # 如果有已拍摄的照片，显示出来
                if 'captured_image' in st.session_state and st.session_state['captured_image']:
                    image_source = st.session_state['captured_image']

            else:
                st.markdown("#### 📁 从本地上传图片")
                uploaded_image = st.file_uploader(
                    "选择图片文件",
                    type=["jpg", "jpeg", "png"],
                    key="uploader",
                    label_visibility="collapsed"
                )
                if uploaded_image:
                    image_source = uploaded_image
                    # 清空拍摄的照片
                    if 'captured_image' in st.session_state:
                        st.session_state['captured_image'] = None

            if image_source:
                st.markdown("---")
                st.markdown("#### 待识别图片")
                st.image(image_source, caption="点击下方按钮开始识别", use_container_width=True)

                if st.button("🔍 识别菜品", type="primary", use_container_width=True):
                    with st.spinner("AI正在识别中..."):
                        image_bytes = image_source.getvalue()
                        results = recognize_dish(image_bytes)

                        if results and len(results) > 0:
                            st.session_state['recognition_results'] = results

                            best_result = results[0]
                            st.session_state['current_dish_result'] = best_result
                            st.session_state['current_dish_name'] = best_result.get("name", "未知")

                            calorie_value = best_result.get("calorie", 0)
                            try:
                                st.session_state['current_dish_calorie'] = float(calorie_value) if isinstance(
                                    calorie_value, str) else calorie_value
                            except:
                                st.session_state['current_dish_calorie'] = 0

                            st.success("✅ 识别成功！")

                            if len(results) > 1:
                                st.markdown("**选择识别结果:**")
                                result_options = []
                                for r in results:
                                    name = r.get('name', '未知')
                                    prob = r.get('probability', 0)
                                    if isinstance(prob, (int, float)):
                                        result_options.append(f"{name} (置信度: {prob:.1%})")
                                    else:
                                        result_options.append(f"{name} (置信度: {prob})")

                                selected_idx = st.selectbox(
                                    "选择最准确的识别结果",
                                    range(len(result_options)),
                                    format_func=lambda x: result_options[x],
                                    key="result_selector"
                                )

                                if st.button("应用选择", key="apply_selection"):
                                    selected_result = results[selected_idx]
                                    st.session_state['current_dish_result'] = selected_result
                                    st.session_state['current_dish_name'] = selected_result.get("name", "未知")
                                    calorie_value = selected_result.get("calorie", 0)
                                    try:
                                        st.session_state['current_dish_calorie'] = float(calorie_value) if isinstance(
                                            calorie_value, str) else calorie_value
                                    except:
                                        st.session_state['current_dish_calorie'] = 0
                                    st.rerun()

                            st.markdown(f"**菜品**: {st.session_state['current_dish_name']}")
                            st.markdown(f"**热量**: {st.session_state['current_dish_calorie']} kcal/100g")

                            probability = best_result.get('probability', 0)
                            if isinstance(probability, (int, float)):
                                st.markdown(f"**置信度**: {probability:.1%}")

                            st.rerun()
                        else:
                            st.error("识别失败，请重试")
            else:
                if input_method == "📷 拍照" and not st.session_state.get('show_camera', False):
                    st.info("👆 点击「打开摄像头」开始拍照")
                elif input_method == "📁 上传图片":
                    st.info("👆 请选择图片文件上传")

        with col2:
            st.subheader("🥗 今日摄入记录")

            if st.session_state['current_dish_result'] is not None:
                dish_name = st.session_state['current_dish_name']
                dish_calorie = st.session_state['current_dish_calorie']

                st.markdown("### 当前识别菜品")
                st.markdown(f"**{dish_name}** - {dish_calorie} kcal/100g")

                with st.form(key="add_dish_form", clear_on_submit=False):
                    portion = st.number_input("份量 (g)", min_value=50, max_value=1000, value=200, step=50)
                    submitted = st.form_submit_button("➕ 添加到今日", type="primary", use_container_width=True)

                    if submitted:
                        if add_dish_to_list(portion):
                            st.success(f"✅ 已添加 {portion}g {dish_name} 到今日记录")
                            st.session_state['current_dish_result'] = None
                            st.session_state['recognition_results'] = []
                            # 清空拍摄的照片
                            if 'captured_image' in st.session_state:
                                st.session_state['captured_image'] = None
                            st.rerun()
                        else:
                            st.error("添加失败，请重试")

                st.markdown("---")

            if st.session_state['dish_list']:
                st.markdown("### 📝 今日已记录")

                total_calorie = sum(d['calorie'] for d in st.session_state['dish_list'])
                remaining = daily_calorie_target - total_calorie

                if remaining >= 0:
                    st.metric("累计摄入", f"{total_calorie:.0f} kcal", delta=f"剩余 {remaining:.0f} kcal")
                else:
                    st.metric("累计摄入", f"{total_calorie:.0f} kcal", delta=f"超出 {abs(remaining):.0f} kcal",
                              delta_color="inverse")

                for i, dish in enumerate(st.session_state['dish_list']):
                    col_a, col_b, col_c, col_d = st.columns([3, 1, 1, 1])
                    with col_a:
                        st.write(f"**{dish['name']}**")
                    with col_b:
                        st.write(f"{dish['portion']}g")
                    with col_c:
                        st.write(f"{dish['calorie']:.0f}kcal")
                    with col_d:
                        if st.button("🗑️", key=f"del_{i}"):
                            st.session_state['dish_list'].pop(i)
                            save_today_dishes(st.session_state['dish_list'])
                            st.rerun()

                if st.button("🗑️ 清除全部记录", use_container_width=True):
                    st.session_state['dish_list'] = []
                    st.session_state['current_dish_result'] = None
                    st.session_state['recognition_results'] = []
                    if 'captured_image' in st.session_state:
                        st.session_state['captured_image'] = None
                    save_today_dishes([])
                    st.rerun()
            else:
                if st.session_state['current_dish_result'] is None:
                    st.info("👆 请先拍照或上传图片，然后点击「识别菜品」")
    # ==================== Tab2: 营养分析 ====================
    with tab2:
        st.header("📊 营养均衡度分析")

        if len(st.session_state['dish_list']) == 0:
            st.info("请先在「拍照识别」页面添加今日菜品")
        else:
            today_nutrients = {k: 0 for k in NUTRIENT_STANDARDS.keys()}
            matched_count = 0
            unmatched_dishes = []

            for dish in st.session_state['dish_list']:
                dish_name = dish['name']
                portion = dish['portion']

                matched_key = find_matching_dish(dish_name)

                if matched_key:
                    nutrition = DISH_NUTRITION_DB[matched_key]
                    matched_count += 1
                else:
                    nutrition = DEFAULT_NUTRITION
                    unmatched_dishes.append(dish_name)

                ratio = portion / 100
                for nutrient in today_nutrients:
                    today_nutrients[nutrient] += nutrition.get(nutrient, 0) * ratio

            if unmatched_dishes:
                st.warning(f"⚠️ 以下菜品未找到精确营养数据，使用估算值: {', '.join(unmatched_dishes)}")
            else:
                st.success(f"✅ 所有菜品营养数据已匹配 ({matched_count}/{len(st.session_state['dish_list'])})")

            standards = {k: NUTRIENT_STANDARDS[k][profile['gender']] for k in NUTRIENT_STANDARDS.keys()}

            achievement_rates = {}
            for nutrient in standards:
                if standards[nutrient] > 0:
                    achievement_rates[nutrient] = (today_nutrients[nutrient] / standards[nutrient]) * 100
                else:
                    achievement_rates[nutrient] = 0

            col1, col2 = st.columns([1, 1])

            with col1:
                st.subheader("📈 营养素达成率雷达图")

                categories = list(standards.keys())
                values = [min(achievement_rates.get(cat, 0), 150) for cat in categories]

                fig = go.Figure()
                fig.add_trace(go.Scatterpolar(
                    r=values, theta=categories, fill='toself',
                    name='达成率 (%)', line_color='#2E86AB'
                ))
                fig.add_trace(go.Scatterpolar(
                    r=[100] * len(categories), theta=categories, fill=None,
                    name='推荐标准 (100%)', line_color='#A23B72', line_dash='dash'
                ))
                fig.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 150], ticksuffix="%")),
                    showlegend=True, height=450
                )
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.subheader("📊 营养素达成率柱状图")

                df_achievement = pd.DataFrame({
                    "营养素": list(achievement_rates.keys()),
                    "达成率": list(achievement_rates.values())
                })
                df_achievement = df_achievement.sort_values("达成率", ascending=False)

                fig_bar = px.bar(
                    df_achievement, x="营养素", y="达成率", color="达成率",
                    color_continuous_scale=["#D62828", "#2A9D8F", "#F77F00"], range_color=[0, 150]
                )
                fig_bar.add_hline(y=100, line_dash="dash", line_color="gray", opacity=0.5)
                fig_bar.add_hline(y=80, line_dash="dot", line_color="#D62828", opacity=0.3)
                fig_bar.add_hline(y=120, line_dash="dot", line_color="#F77F00", opacity=0.3)
                fig_bar.update_layout(height=450, showlegend=False)
                st.plotly_chart(fig_bar, use_container_width=True)

            st.subheader("📋 详细营养数据")

            detail_data = []
            for nutrient in standards.keys():
                status = "✅ 适宜" if 80 <= achievement_rates[nutrient] <= 120 else (
                    "⚠️ 不足" if achievement_rates[nutrient] < 80 else "⚠️ 过量")
                detail_data.append({
                    "营养素": nutrient,
                    "今日摄入": f"{today_nutrients[nutrient]:.1f} {NUTRIENT_STANDARDS[nutrient]['单位']}",
                    "推荐标准": f"{standards[nutrient]} {NUTRIENT_STANDARDS[nutrient]['单位']}",
                    "达成率": f"{achievement_rates[nutrient]:.0f}%",
                    "状态": status
                })

            st.dataframe(pd.DataFrame(detail_data), use_container_width=True, hide_index=True)

            st.subheader("💡 智能营养建议")

            lacking_nutrients = [n for n, rate in achievement_rates.items() if rate < 80]
            excess_nutrients = [n for n, rate in achievement_rates.items() if rate > 120]

            col_lack, col_excess = st.columns(2)

            with col_lack:
                st.markdown(f"**🔴 需要补充的营养素（基于{profile['region']}饮食习惯）**")
                if lacking_nutrients:
                    for nutrient in lacking_nutrients:
                        foods = get_region_foods(nutrient, profile['region'])
                        st.markdown(f"- **{nutrient}**: 建议补充 **{'、'.join(foods[:3])}**")
                else:
                    st.markdown("✅ 暂无明显不足的营养素")

            with col_excess:
                st.markdown("**🟠 摄入偏多的营养素**")
                if excess_nutrients:
                    for nutrient in excess_nutrients:
                        st.markdown(f"- **{nutrient}**: 建议适当减少相关食物摄入")
                else:
                    st.markdown("✅ 暂无摄入过量的营养素")

            today_total = sum(d['calorie'] for d in st.session_state['dish_list'])
            st.markdown("---")
            st.subheader("📖 与卫健委推荐食谱对比")
            st.markdown(f"""
            - 总热量目标: **{daily_calorie_target} kcal** (今日已摄入: **{today_total:.0f} kcal**)
            - 蛋白质: **{standards['蛋白质']}g** (占比15-20%)
            - 脂肪: **{standards['脂肪']}g** (占比20-30%)
            - 碳水: **{standards['碳水']}g** (占比50-60%)
            - 膳食纤维: **≥{standards['膳食纤维']}g**
            """)

    # ==================== Tab3: 本周报告 ====================
    with tab3:
        st.header("📝 本周报告")

        week_summary = get_week_summary()

        st.subheader(f"📊 本周营养统计 ({week_summary['week_key']} 周)")

        if week_summary['days_recorded'] == 0:
            st.info("本周暂无记录数据")
        else:
            avg_daily_calories = week_summary['total_calories'] / week_summary['days_recorded']

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("记录天数", f"{week_summary['days_recorded']} 天")
            col2.metric("总摄入", f"{week_summary['total_calories']:.0f} kcal")
            col3.metric("日均摄入", f"{avg_daily_calories:.0f} kcal")
            col4.metric("vs目标",
                        f"{'+' if avg_daily_calories > daily_calorie_target else '-'}{abs(daily_calorie_target - avg_daily_calories):.0f} kcal")

            st.subheader("📈 本周每日热量摄入趋势")

            week_dates = []
            week_calories = []
            monday = datetime.strptime(week_summary['week_key'], "%Y-%m-%d")

            for i in range(7):
                date = monday + timedelta(days=i)
                date_key = date.strftime("%Y-%m-%d")
                week_dates.append(date.strftime("%m/%d"))
                week_calories.append(week_summary['daily_calories'].get(date_key, 0))

            df_week = pd.DataFrame({"日期": week_dates, "热量": week_calories})

            fig_week = px.bar(df_week, x="日期", y="热量", title="每日热量摄入", labels={"热量": "热量 (kcal)"})
            fig_week.add_hline(y=daily_calorie_target, line_dash="dash", line_color="red",
                               annotation_text=f"目标: {daily_calorie_target}kcal")
            st.plotly_chart(fig_week, use_container_width=True)

    # ==================== Tab4: 历史周报 ====================
    with tab4:
        st.header("📅 历史周报")

        available_weeks = get_available_weeks()

        if len(available_weeks) == 0:
            st.info("暂无历史数据")
        else:
            selected_week = st.selectbox(
                "选择查看的周", available_weeks,
                format_func=lambda x: f"{x} 周"
            )

            if selected_week:
                history_summary = get_week_summary(selected_week)

                st.subheader(f"📊 {selected_week} 周 营养统计")

                if history_summary['days_recorded'] == 0:
                    st.info("该周无记录数据")
                else:
                    avg_calories = history_summary['total_calories'] / history_summary['days_recorded']

                    col1, col2, col3 = st.columns(3)
                    col1.metric("记录天数", f"{history_summary['days_recorded']} 天")
                    col2.metric("总摄入", f"{history_summary['total_calories']:.0f} kcal")
                    col3.metric("日均摄入", f"{avg_calories:.0f} kcal")

                    week_dates = []
                    week_calories = []
                    monday = datetime.strptime(selected_week, "%Y-%m-%d")

                    for i in range(7):
                        date = monday + timedelta(days=i)
                        date_key = date.strftime("%Y-%m-%d")
                        week_dates.append(date.strftime("%m/%d"))
                        week_calories.append(history_summary['daily_calories'].get(date_key, 0))

                    df_history = pd.DataFrame({"日期": week_dates, "热量": week_calories})

                    fig_history = px.bar(df_history, x="日期", y="热量",
                                         title=f"{selected_week}周 每日热量摄入")
                    fig_history.add_hline(y=daily_calorie_target, line_dash="dash", line_color="red")
                    st.plotly_chart(fig_history, use_container_width=True)

    # 页脚
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: gray; padding: 20px;'>
    🥗 食析智导 -基于 DRIs 标准的地域化膳食系统 | 基于百度AI菜品识别 + 卫健委体重管理指南<br/>
    数据自动保存至本地，每周一自动开始新的一周
    </div>
    """, unsafe_allow_html=True)


# ==================== 主入口 ====================
def main():
    if not st.session_state['logged_in']:
        login_page()
    elif not st.session_state['profile_completed']:
        profile_page()
    else:
        main_app()


if __name__ == "__main__":
    main()