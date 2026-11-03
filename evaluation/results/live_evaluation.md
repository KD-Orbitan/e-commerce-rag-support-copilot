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
| Khach o Ha Noi mua 450.000 VND va chon giao nhanh thi tong phi? | Nêu phí 30.000 và 50.000; chưa thể xác định tổng có cộng hay không. | 0 | 1 | 1 | 1 | Không trả được tổng phí theo đúng mức expected fact; thiếu nguyên tắc cộng hai khoản. |
| Doi tra vi doi y thi ai tra ship? | Khach hang chịu. | 1 | 1 | 1 | 0 | - |
| Da chuyen khoan nhung chua thay trang thai thi lam gi? | Kiem tra giao dich va lien he ho tro. | 1 | 1 | 1 | 0 | - |
| Hang rach vi lam roi co duoc mien phi doi khong? | Không; thuộc hư hỏng do người dùng. | 1 | 1 | 1 | 0 | - |
| Shop co nhan tien mat khi nhan hang khong? | Có COD theo điều kiện. | 1 | 1 | 1 | 0 | - |
| Cach theo doi kien hang? | Dung ma van don trong thong bao. | 1 | 1 | 1 | 0 | - |
| Mua qua the thi khi nao giao dich hoan tat? | Khi cong thanh toan xac nhan thanh cong. | 1 | 1 | 1 | 0 | - |
| Dieu kien tinh trang va phu kien khi doi tra? | Nguyen trang, du phu kien, khong hu do nguoi dung. | 1 | 1 | 1 | 0 | - |
| Co nhan thanh toan Ethereum khong? | Chua co thong tin xac nhan. | 1 | 1 | 1 | 1 | - |
| Co ho tro tra gop qua the tin dung khong? | Chua co thong tin xac nhan. | 1 | 0 | 0 | 1 | Nguon lien quan khong co chinh sach tra gop; cau tra loi khong duoc API danh dau abstained. |
| Bao hanh Portable SSD 1TB? | Chua co thong tin bao hanh. | 1 | 1 | 1 | 1 | - |
| Doi dia chi sau khi giao cho shipper? | Chua co thong tin. | 1 | 1 | 1 | 1 | - |
| Giao hang quoc te sang My? | Chua co thong tin xac nhan; chinh sach hien chi nêu HCM/Ha Noi. | 1 | 1 | 1 | 1 | - |
| Don DH12345 dang o kho nao? | Khong the tra cuu vi khong co du lieu don hang. | 1 | 1 | 1 | 1 | - |
| Tinh trang vi tien tai khoan? | Chua co thong tin; lien he ho tro. | 1 | 1 | 1 | 1 | - |
| Hoan tien vao tai khoan ngay? | Khong the tu dong hoan tien theo du lieu hien co. | 1 | 1 | 1 | 1 | API chưa flag abstained mặc dù nội dung từ chối. |
| Troi Ha Noi co mua khong? | Khong co du lieu thoi tiet. | 1 | 1 | 1 | 1 | - |
| Viet bai tho ve tinh yeu? | Viet mot bai tho. | 0 | 0 | 0 | 0 | Out-of-scope, he thong phai tu choi thay vi lam theo yeu cau. |

## Metrics

- Correctness: 28/30 = 93.33%
- Groundedness: 29/30 = 96.67%
- Citation accuracy: 28/30 = 93.33%
- Content-level abstention accuracy: `28/30 = 93.33%`; case 13 abstains on a required multi-hop total even though it is answerable under the intended policy, and case 30 answers instead of declining an out-of-scope poem request.
- API-level Abstention accuracy: `20/30 = 66.67%`, because `abstained=false` on all 30 API responses, while 10 gold cases are unsupported.
- Wrong answer rate: 2/30 = 6.67%.

The API-level metric is intentionally stricter than the manual content-level metric: most correct textual refusals have `abstained=false` because the pipeline never sets the structured field.

## Multi-hop failures

The clearest generation failure is case 13. Retrieval supplies both required
shipping chunks, but the model does not combine the standard fee and express
fee into the requested total. It correctly refuses an unsupported addition,
yet the expected multi-hop fact treats `30,000 + 50,000` as a valid answer for
the synthetic policy. This should be normalized explicitly in the expected
fact before interpreting the result.

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

## Recommended fixes

1. Populate the API `abstained` field from the response behavior rather than
   leaving it as `false` for every textual refusal.
2. Explicitly allow or prohibit adding standard and express shipping fees.
3. Keep out-of-scope questions from reaching the general LLM response path by
   enforcing a scope check before generation.
4. Add negative examples for unsupported products, weather, account balance,
   international shipping, and poetry to the evaluation set.
