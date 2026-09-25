Nên viết thành **“Test Selection Guide”**, không phải tài liệu giải thích từng loại test riêng lẻ.

Cấu trúc tốt nhất là:

# Test Selection Guide

## 1. Mục tiêu

> Khi implement một feature, developer phải xác định các rủi ro có thể xảy ra và chọn loại test phù hợp để chứng minh feature hoạt động đúng.

**Nguyên tắc:**

> **Risk → Question → Test type**

---

## 2. Decision table — phần quan trọng nhất

| Câu hỏi cần trả lời                                             | Nếu YES → viết test              |
| --------------------------------------------------------------- | -------------------------------- |
| Logic/code có đúng không?                                       | **Unit**                         |
| Các component/module phối hợp đúng không?                       | **Integration**                  |
| API request/response có đúng contract không?                    | **API**                          |
| Các service có giao tiếp đúng contract không?                   | **Contract**                     |
| Business flow end-to-end có đúng không?                         | **E2E**                          |
| Request có thể được gửi lại không?                              | **Idempotency**                  |
| Nhiều request có thể chạy đồng thời không?                      | **Concurrency / Race Condition** |
| Có transaction hoặc shared DB state không?                      | **Transaction / Isolation**      |
| Thay đổi có thể phá behavior cũ không?                          | **Regression**                   |
| Sau deployment hệ thống có hoạt động không?                     | **Smoke**                        |
| Hệ thống có đáp ứng khi tải tăng không?                         | **Performance / Load / Stress**  |
| Có thể truy cập trái phép / input độc hại không?                | **Security**                     |
| Dependency/infrastructure bị lỗi thì hệ thống xử lý đúng không? | **Resilience / Chaos**           |

Đây nên là **trang đầu tiên** dev nhìn thấy.

---

# 3. Decision flow

Cho dev một flow cực ngắn:

```text
Feature
  │
  ├─ Logic? ───────────────→ Unit
  │
  ├─ Component interaction? → Integration
  │
  ├─ API? ──────────────────→ API
  │
  ├─ Service-to-service? ───→ Contract
  │
  ├─ Business flow? ────────→ E2E
  │
  ├─ Retry possible? ───────→ Idempotency
  │
  ├─ Concurrent access? ────→ Concurrency
  │
  ├─ DB transaction/state? ─→ Transaction/Isolation
  │
  ├─ Security boundary? ────→ Security
  │
  ├─ High traffic? ─────────→ Performance
  │
  └─ Failure/dependency? ───→ Resilience
```

**Một feature có thể cần nhiều loại test.**

---

# 4. Test type catalog

Sau decision table mới giải thích từng loại:

### Unit

**Question:**

> Một đơn vị logic có hoạt động đúng độc lập không?

**Dùng khi:**

* business logic
* calculation
* validation
* transformation

**Không dùng để:** test DB/network/external service.

---

### Integration

**Question:**

> Các thành phần thật có phối hợp đúng không?

**Dùng khi:**

* Service + DB
* Repository + DB
* Service + Redis
* module A + module B

---

### API

**Question:**

> API có đúng behavior và contract không?

Test:

```text
request
→ status code
→ response
→ validation
→ authentication/authorization
```

---

### E2E

**Question:**

> Một business flow hoàn chỉnh có hoạt động không?

Ví dụ:

```text
Login
→ Add product
→ Checkout
→ Payment
→ Order completed
```

---

### Contract

**Question:**

> Service A và Service B có hiểu nhau đúng không?

Ví dụ:

```text
Order Service
      ↓
Payment Service
```

---

### Concurrency

**Question:**

> Điều gì xảy ra khi nhiều operation chạy cùng lúc?

Ví dụ:

```text
Stock = 1

Request A ─┐
           ├→ Buy product
Request B ─┘
```

---

### Idempotency

**Question:**

> Nếu cùng một operation được gửi nhiều lần thì state có bị sai không?

Ví dụ:

```text
POST /payment
Idempotency-Key: ABC

→ retry
→ retry
→ retry
```

Expected:

```text
1 payment
```

---

### Transaction / Isolation

**Question:**

> Database có giữ được invariant khi transaction thành công, rollback hoặc chạy đồng thời không?

---

### Regression

**Question:**

> Code mới có làm behavior cũ hỏng không?

Lưu ý:

**Regression không nhất thiết là một framework/test suite riêng.**

Nó là mục tiêu của việc chạy lại các test hiện có sau thay đổi.

---

### Smoke

**Question:**

> Sau deployment, hệ thống có những chức năng cơ bản còn sống không?

---

### Performance

**Question:**

> Hệ thống đáp ứng SLA/SLO dưới tải yêu cầu không?

---

### Security

**Question:**

> Người dùng không hợp lệ có thể làm điều họ không được phép không?

Ví dụ:

```text
Authentication
Authorization
Input validation
Injection
Data exposure
Privilege escalation
```

---

### Resilience / Chaos

**Question:**

> Dependency hoặc infrastructure chết thì hệ thống phản ứng thế nào?

Ví dụ:

```text
Redis DOWN
DB timeout
Payment Service DOWN
Network latency
```

---

# 5. Cuối tài liệu nên có "Feature Test Checklist"

Đây mới là thứ dev dùng hàng ngày:

```text
## Feature Test Checklist

### Correctness
[ ] Unit
[ ] Integration
[ ] API
[ ] E2E

### Distributed system
[ ] Contract
[ ] Idempotency
[ ] Concurrency
[ ] Transaction / Isolation

### Non-functional
[ ] Security
[ ] Performance
[ ] Resilience

### Change & Deployment
[ ] Regression
[ ] Smoke
```

Nhưng **không phải tick tất cả**.

Dev phải tick những mục có **risk tương ứng**.

---

# 6. Tôi sẽ thêm một rule bắt buộc

Trong PR template:

```text
## Testing

### Tests added
- [ ] Unit
- [ ] Integration
- [ ] API
- [ ] Contract
- [ ] E2E
- [ ] Concurrency
- [ ] Idempotency
- [ ] Transaction / Isolation
- [ ] Security
- [ ] Performance
- [ ] Resilience

### Not applicable
- Type:
- Reason:
```

Ví dụ:

```text
### Not applicable
- Concurrency
- Reason: feature only reads immutable data.

- Idempotency
- Reason: GET endpoint, no state mutation.
```

Điều này tốt hơn việc bắt dev **mặc định phải viết tất cả test**.

---

## Tóm lại

Tài liệu nên có **4 phần**:

```text
1. PRINCIPLE
   Risk → Question → Test

2. DECISION TABLE
   "Nếu câu hỏi này → dùng test này"

3. TEST CATALOG
   Giải thích từng loại + khi nào dùng + ví dụ

4. PR CHECKLIST
   Dev tự xác nhận những test nào cần/không cần
```

Nếu mục tiêu là đưa cho **một developer mới vào team**, tôi sẽ viết tài liệu khoảng **2–4 trang**, trong đó **Decision Table + vài ví dụ thực tế chiếm phần lớn**, thay vì viết một tài liệu dài 20 trang giải thích lý thuyết testing.
