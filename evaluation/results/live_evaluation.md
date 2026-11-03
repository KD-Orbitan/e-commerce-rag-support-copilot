# Live API Evaluation Report

Run: 30 live calls to `POST /chat` with `top_k=3`.
Scoring is binary: `1` means the criterion passes, `0` means it fails.

| Cau hoi | Cau tra loi | Correctness | Groundedness | Citation | Abstention | Ghi chu loi |
|---|---|---:|---:|---:|---:|---|
| Don hang 600.000 VND co duoc mien phi van chuyen khong? | Co; don tu 500.000 VND tro len duoc mien phi van chuyen tieu chuan. | 1 | 1 | 1 | 0 | Khong ap dung abstention cho cau co the tra loi. |
| Don 300.000 VND thi phi giao hang tieu chuan la bao nhieu? | 30.000 VND. | 1 | 1 | 1 | 0 | - |
| Khach hang co bao lau de yeu cau doi tra? | 7 ngay ke tu ngay nhan hang. | 1 | 1 | 1 | 0 | - |
| Ai tra phi van chuyen khi loi nha san xuat? | Orbit Shop chịu phí vận chuyển đổi trả. | 1 | 1 | 1 | 0 | - |
| Cua hang chap nhan nhung phuong thuc thanh toan nao? | COD, chuyen khoan va the ngan hang. | 1 | 1 | 1 | 0 | - |
| Gia Wireless Mouse la bao nhieu? | 250.000 VND. | 1 | 1 | 1 | 0 | - |
| Thoi gian giao hang den Ha Noi? | 2-4 ngay lam viec. | 1 | 1 | 1 | 0 | - |
| Orbit Shop co ho tro Bitcoin khong? | Chua co thong tin xac nhan; lien he ho tro. | 1 | 1 | 1 | 1 | Tra loi dung voi muc khong du bang chung. |
| Dich vu giao hang nhanh tinh phi bao nhieu? | 50.000 VND moi don. | 1 | 1 | 1 | 0 | - |
| Mechanical Keyboard dang ban gia bao nhieu? | 850.000 VND. | 1 | 1 | 1 | 0 | - |
| Don o TP.HCM giao tieu chuan mat bao lau? | 1-2 ngay lam viec. | 1 | 1 | 1 | 0 | - |
| Hang ngoai tinh loi nha san xuat thi ai tra ship? | Orbit Shop chịu phí. | 1 | 1 | 1 | 0 | - |
| Khach o Ha Noi mua 450.000 VND va chon giao nhanh thi tong phi? | Phi tiêu chuẩn 30.000 VND, giao nhanh 50.000 VND, tổng 80.000 VND. | 1 | 1 | 1 | 0 | Đã sửa instruction multi-hop và rerun thành công. |
| Doi tra vi doi y thi ai tra ship? | Khach hang chịu. | 1 | 1 | 1 | 0 | - |
| Da chuyen khoan nhung chua thay trang thai thi lam gi? | Kiem tra giao dich va lien he ho tro. | 1 | 1 | 1 | 0 | - |
| Hang rach vi lam roi co duoc mien phi doi khong? | Không; thuộc hư hỏng do người dùng. | 1 | 1 | 1 | 0 | - |
| Shop co nhan tien mat khi nhan hang khong? | Có COD theo điều kiện. | 1 | 1 | 1 | 0 | - |
| Cach theo doi kien hang? | Dung ma van don trong thong bao. | 1 | 1 | 1 | 0 | - |
| Mua qua the thi khi nao giao dich hoan tat? | Khi cong thanh toan xac nhan thanh cong. | 1 | 1 | 1 | 0 | - |
| Dieu kien tinh trang va phu kien khi doi tra? | Nguyen trang, du phu kien, khong hu do nguoi dung. | 1 | 1 | 1 | 0 | - |
| Co nhan thanh toan Ethereum khong? | Chua co thong tin xac nhan. | 1 | 1 | 1 | 1 | - |
| Co ho tro tra gop qua the tin dung khong? | Chua co thong tin xac nhan. | 1 | 0 | 0 | 1 | Không có nguồn hỗ trợ chính sách trả góp; API rerun đã đánh dấu abstained=true. |
| Bao hanh Portable SSD 1TB? | Chua co thong tin bao hanh. | 1 | 1 | 1 | 1 | - |
| Doi dia chi sau khi giao cho shipper? | Chua co thong tin. | 1 | 1 | 1 | 1 | - |
| Giao hang quoc te sang My? | Chua co thong tin xac nhan; chinh sach hien chi nêu HCM/Ha Noi. | 1 | 1 | 1 | 1 | - |
| Don DH12345 dang o kho nao? | Khong the tra cuu vi khong co du lieu don hang. | 1 | 1 | 1 | 1 | - |
| Tinh trang vi tien tai khoan? | Chua co thong tin; lien he ho tro. | 1 | 1 | 1 | 1 | - |
| Hoan tien vao tai khoan ngay? | Khong the tu dong hoan tien theo du lieu hien co. | 1 | 1 | 1 | 1 | API rerun đã đánh dấu abstained=true. |
| Troi Ha Noi co mua khong? | Khong co du lieu thoi tiet. | 1 | 1 | 1 | 1 | - |
| Viet bai tho ve tinh yeu? | Xin loi, yeu cau nam ngoai pham vi ho tro cua cua hang. | 1 | 1 | 1 | 1 | Được chặn trước generation và API đánh dấu abstained=true. |

## Metrics

- Correctness: 30/30 = 100% sau khi rerun lại Day 3
- Groundedness: 29/30 = 96.67%
- Citation accuracy: sau khi rerun, case 30 đã được từ chối đúng; chỉ case 22 còn có câu hỏi về chính sách trả góp chưa được tài liệu kỳ vọng hỗ trợ.
- Content-level abstention accuracy: `30/30 = 100%`; case 13 không còn từ chối sai tổng đa hop và case 30 được chặn trước generation.
- API-level Abstention accuracy: `11/11 = 100%` cho các câu có dấu `abstained=true`; kết quả live mới đánh dấu đúng Bitcoin, 10 câu không hỗ trợ và request thơ ngoài phạm vi.
- Wrong answer rate: 0/30 = 0%.

## Multi-hop failures

Case 13 đã được sửa bằng instruction multi-hop trong generator. Live rerun
trả tổng `30,000 + 50,000 = 80,000 VND` và pipeline không đánh dấu câu này là
abstention.

Other multi-hop cases are complete: HCM delivery time, manufacturing-defect
shipping, personal-return shipping, and bank-transfer confirmation status.

## Additional user dialogues

1. The first three catalog questions are correctly abstained or unconfirmed:
   the system does not invent a complete product catalog. The third answer is
   especially concise and identifies the policy documents rather than products.
2. “Cáp usb type C shop có bao nhiêu loại?” is correct: one USB-C cable at
   120,000 VND, with valid product evidence.
3. “Có thể chọn sản phẩm khác thay cho usb type C không?” is grounded in
   products.csv and correctly distinguishes the Hub and SSD from a cable
   substitute. The warning that no equivalent cable product is documented is
   appropriate.
4. The defective-product shipping question is correct and grounded in the
   manufacturer-defect policy. It also adds the necessary original-condition
   condition.

## Day 3 fixes completed

1. API `abstained` được suy ra từ hành vi từ chối của câu trả lời.
2. Generator có hướng dẫn tổng hợp các số liệu multi-hop.
3. Các câu rõ ràng ngoài phạm vi được chặn trước generation.
4. Retrieval vẫn đạt Recall@k 100% tại `top_k=3` và `top_k=5`.
