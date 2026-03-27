import sqlite3
import pandas as pd
from datetime import datetime

# 1. 链接到你的数据库（这里假设你的数据库文件叫 data.db，请根据实际情况修改）
DB_PATH = "data.db" 

def export_to_csv():
    try:
        # 2. 连接数据库
        conn = sqlite3.connect(DB_PATH)
        
        # 3. 使用 Pandas 直接读取整个表（假设表名是 user_preferences）
        # 如果你的表名不一样，请把 'user_preferences' 换成你代码里建表的真实名称
        df = pd.read_sql_query("SELECT * FROM user_preferences", conn)
        
        # 4. 生成带时间戳的文件名，防止覆盖
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"fairshare_data_{timestamp}.csv"
        
        # 5. 导出为 CSV
        df.to_csv(filename, index=False)
        print(f"✅ 成功！已从数据库提取 {len(df)} 条数据，并保存为: {filename}")
        
    except Exception as e:
        print(f"❌ 导出失败: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    export_to_csv()
