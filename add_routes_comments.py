import re

with open(r'e:\code\File_Do_An\src\backend\app\api\routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add health comment
content = re.sub(
    r'(@router\.get\(\"/health\"\)\s*def health\(\) -> dict:)',
    r'\1\n    """\n    API kiểm tra trạng thái Backend (Health Check).\n    Frontend thường gọi API này đầu tiên để đảm bảo Backend đang chạy.\n    """',
    content
)

# Add predict_drug_to_disease comment
content = re.sub(
    r'(@router\.post\(\"/predict/drug-to-disease\", response_model=PredictResponse\)\s*def predict_drug_to_disease\([\s\S]*?\)\s*-> PredictResponse:)',
    r'\1\n    """\n    API cốt lõi: Dự đoán các loại Bệnh mà 1 loại Thuốc có thể chữa trị.\n    - Gọi logic AI (predict_diseases_by_drug_name).\n    - Lưu lại lịch sử dự đoán vào Database (repo.add_prediction).\n    """',
    content
)

# Add predict_disease_to_drug comment
content = re.sub(
    r'(@router\.post\(\"/predict/disease-to-drug\", response_model=PredictResponse\)\s*def predict_disease_to_drug\([\s\S]*?\)\s*-> PredictResponse:)',
    r'\1\n    """\n    API cốt lõi: Dự đoán các loại Thuốc có khả năng chữa trị 1 loại Bệnh.\n    Sử dụng AI logic (predict_drugs_by_disease_name) và ghi lại lịch sử.\n    """',
    content
)

with open(r'e:\code\File_Do_An\src\backend\app\api\routes.py', 'w', encoding='utf-8') as f:
    f.write(content)
