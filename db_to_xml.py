import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime
import os

def calculate_age(dob):
    try:
        birth = datetime.strptime(dob, "%Y-%m-%d")
        today = datetime.today()
        return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
    except:
        return None

def get_age_group(age):
    if age is None:
        return "Unknown"
    if age < 18:
        return "Under 18"
    elif age < 30:
        return "18–29"
    elif age < 45:
        return "30–44"
    elif age < 60:
        return "45–59"
    return "60+"

def db_to_rich_xml(db_path, output_file="full_usage_data.xml"):
    if not os.path.exists(db_path):
        print(f"❌ Error: '{db_path}' not found.")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Join query to get everything
        cursor.execute("""
            SELECT 
                u.name as user_name,
                u.email,
                u.sex,
                u.dob,
                e.name as equipment_name,
                e.type as equipment_type,
                us.usage_date,
                us.end_usage_date,
                us.hours_used
            FROM usage us
            JOIN users u ON us.user_id = u.id
            JOIN equipment e ON us.equipment_id = e.id
        """)

        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

        root = ET.Element("GymUsageData")

        for row in rows:
            usage = ET.SubElement(root, "UsageEntry")
            data = dict(zip(columns, row))

            # Add original fields
            for col, val in data.items():
                child = ET.SubElement(usage, col)
                child.text = str(val) if val is not None else ""

            # Add calculated fields
            age = calculate_age(data["dob"])
            age_group = get_age_group(age)

            ET.SubElement(usage, "age").text = str(age) if age is not None else "Unknown"
            ET.SubElement(usage, "age_group").text = age_group

        # Output to file
        tree = ET.ElementTree(root)
        tree.write(output_file, encoding="utf-8", xml_declaration=True)
        print(f"✅ Done! Rich XML data written to '{output_file}'")

    except Exception as e:
        print("❌ Error during export:", e)
    finally:
        conn.close()


# 🟢 SETUP
db_path = "gym.db"  # Make sure this file exists in the same folder
output_file = "full_usage_data.xml"

# 🚀 Run it
db_to_rich_xml(db_path, output_file)
