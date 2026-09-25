Gốc của mọi rủi ro là thế này: trong Clio, gate là nguồn sự thật duy nhất cho câu hỏi "task đã xong chưa". `/clio:memo` chỉ tick khi gate `OK`. Từ đó kết quả lan ra plan (`[x]`), `index.jsonl` (built) và `clio:context` của các phiên sau. Vì vậy một lần `OK` sai không dừng ở một task mà được ghi thành lịch sử "đã chứng minh", mà ledger của Clio lại là append-only, không sửa được.

**1. Red/flaky không gắn với `fp`**
- **Cơ chế:** chạy lại đến khi xanh vẫn qua. Test không bao giờ đỏ (kể cả `true`) cũng qua với task thường. Case regression có thể được tính "đã đỏ" nhờ một lần fail do flaky. (Đã tái hiện.)
- **Hậu quả trong Clio:**
  - Flaky không bao giờ vào `debt.jsonl`, vì luật "flaky → `code-debt`" chỉ kích hoạt khi gate FAIL. Ledger "owed" vì thế thiếu đúng loại nợ nguy hiểm nhất.
  - Concurrency flaky thường là race condition thật. Nó được ghi là đã test, trong khi đó chính là nhóm task critical (tiền, auth).
  - Regression chưa từng tái hiện bug vẫn được ghi là đã chứng minh, nên bug có thể quay lại mà suite vẫn xanh.
  - Khi re-plan, `coverage` thấy `pass` nên không đẻ sub-task "Harden". Lỗ hổng tự che chính nó.
- **Mức độ:** cao. Lời hứa "done = đã chứng minh" thành "done = exit 0".

**2. Evidence không gắn với định nghĩa case và bảng đã duyệt**
- **Cơ chế:** có thể nới `Expected`, giảm `Repeat` hoặc xóa case đang fail mà gate vẫn `OK`. Không để lại dấu vết vì `.claude/` bị loại khỏi `fp` và tests doc không phải ledger append-only. (Xóa case đã tái hiện; nới `Expected` suy ra từ code.)
- **Hậu quả trong Clio:**
  - Việc user duyệt bảng case ("the case list is the definition of done") mất ý nghĩa, vì bảng có thể đổi sau khi duyệt mà user không biết.
  - Trái với nguyên tắc cốt lõi của Clio là không sửa âm thầm và chỉ append. Tests doc là chỗ duy nhất trong luồng bị sửa âm thầm được.
  - Người thực hiện đồng thời là model tự viết test. Khi bị áp lực "phải qua gate", đường ít kháng cự nhất là sửa bảng thay vì sửa code. Đây là suy luận, nhưng đúng kiểu hành vi mà Clio sinh ra để chặn.
- **Mức độ:** cao. Gian lận có chủ đích hay vô tình đều không phát hiện được.

**3. Mutation không được kiểm**
- **Cơ chế:** ngưỡng và phạm vi nằm trong command do model viết, nên `--thresholds.break 0` hoặc chạy trên sai file vẫn qua. (Suy ra từ code.)
- **Hậu quả trong Clio:**
  - Mutation chỉ bắt buộc với task critical (tiền, auth, concurrency, xóa dữ liệu). Như vậy gate yếu nhất đúng ở chỗ rủi ro lớn nhất.
  - Plan và ledger ghi "critical, đã có mutation", tạo cảm giác an toàn giả cho đúng phần code cần tin nhất.
- **Mức độ:** trung bình đến cao. Phạm vi hẹp nhưng hậu quả nặng.

**4. Plan ↔ test thiếu đường xử lý và kiểm tra đầu vào**
- **Cơ chế:** level không áp dụng được thì không có đường supersede, nên gate FAIL mãi. Gõ sai tên level cũng bị kẹt như vậy. Gate vẫn chạy trên row đã `superseded`. Dấu `|` làm lệch cột, nên script có thể đọc sai command. (Đọc code, chưa chạy.)
- **Hậu quả trong Clio:**
  - Kẹt vĩnh viễn thì user sẽ bỏ qua gate (tick tay, tắt skill), và kỷ luật của cả hệ sụp dần.
  - Hoặc model bị ép bịa ra case để "phủ" level đó, ví dụ `perf` với ngưỡng tự nghĩ ra. Điều này vi phạm trực tiếp luật "never invent a threshold" và dẫn ngược về vấn đề 1 và 2.
  - Gate trên row superseded làm ledger rối: tick nhầm row, `index.jsonl` trỏ sai task.
  - Parse lệch có thể làm chạy sai command mà vẫn ghi `pass`.
- **Mức độ:** trung bình. Chủ yếu gây gate FAIL oan, nhưng áp lực đó lại đẩy người dùng hoặc model về phía gian lận.

**Rủi ro tổng thể**
- **Lỗi cộng dồn:** task sau `Needs` task trước, nên một `[x]` sai trở thành nền cho cả chuỗi phía sau.
- **Mất niềm tin:** giá trị của Clio là phân biệt decided, built và owed. Nếu "built" không đáng tin thì `clio:context` trả về thông tin sai với vẻ tự tin, tức là đúng thứ ảo giác mà Clio định chống.
- **Khó sửa về sau:** ledger append-only nên record sai không xóa được. Chỉ có thể thêm record đính chính, và phải biết là sai thì mới đính chính được.