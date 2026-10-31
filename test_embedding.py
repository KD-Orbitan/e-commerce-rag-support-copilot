
import os
from dotenv import load_dotenv
from openai import OpenAI

# Đọc API key từ file .env
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("Không tìm thấy OPENAI_API_KEY trong file .env")

# Khởi tạo OpenAI client
client = OpenAI(api_key=api_key)

# Gửi một câu thử nghiệm để tạo embedding
response = client.embeddings.create(
    model="text-embedding-3-small",
    input="Chính sách giao hàng của cửa hàng Orbit Shop"
)

# Chỉ in kết quả kiểm tra, không in API key
vector = response.data[0].embedding

print("Kết nối OpenAI API thành công!")
print(f"Model: {response.model}")
print(f"Vector dimensions: {len(vector)}")
print(f"Token usage: {response.usage.total_tokens}")
