I. Phần core tool cơ bản
📦 LỚP 1: PHÂN HỆ QUẢN LÝ TỒN KHO & SƠ ĐỒ KHO (INVENTORY & SLOTTING)
Nhóm công cụ này giúp AI Agent thấu hiểu vị trí, trạng thái vật lý và tính chất của hàng hóa trong kho để đưa ra quyết định hoặc viết code xử lý.

1. check_stock_availability
Mô tả: Lấy thông tin tồn kho thực tế (Physical Qty) và tồn kho khả dụng để xuất (Available Qty) của một mã sản phẩm (SKU) tại một kho cụ thể.

Tham số đầu vào (inputSchema):

sku_code (string, bắt buộc): Mã sản phẩm (ví dụ: SKU-1060-6GB).

warehouse_id (integer, tùy chọn): ID của chi nhánh kho.

2. inspect_shelf_capacity
Mô tả: Kiểm tra dung lượng và không gian còn trống của một kệ hàng (Shelf/Location) cụ thể dựa trên thể tích vật lý.

Tham số đầu vào (inputSchema):

location_code (string, bắt buộc): Mã vị trí kệ kho (ví dụ: ZONE-A-ROW-02-SHELF-01).

3. abc_analysis_report
Mô tả: Trả về phân loại ABC của một mặt hàng dựa trên tần suất xuất kho và giá trị (Nhóm A: hàng hot, Nhóm B: hàng trung bình, Nhóm C: hàng chậm).

Tham số đầu vào (inputSchema):

sku_code (string, bắt buộc).

4. smart_slotting_optimizer
Mô tả: Gợi ý vị trí sắp xếp tối ưu nhất cho một mã hàng chuẩn bị nhập kho dựa trên phân loại ABC của nó (ví dụ: Hàng nhóm A phải xếp gần cửa xuất).

Tham số đầu vào (inputSchema):

sku_code (string, bắt buộc).

quantity (integer, bắt buộc): Số lượng kiện sắp nhập.

🔄 LỚP 2: PHÂN HỆ THAO TÁC & DỊCH CHUYỂN KHO (TRANSACTIONS & MOVEMENTS)
Nhóm công cụ có quyền Ghi (Write) vào Database, giúp AI có thể trực tiếp thực hiện lệnh điều hành hoặc tự tạo dữ liệu test.

5. update_inventory_quantity
Mô tả: Cập nhật tăng/giảm trực tiếp số lượng tồn kho của một SKU tại một vị trí cố định (Thường dùng cho luồng Nhập kho - Inbound hoặc Xuất kho - Outbound).

Tham số đầu vào (inputSchema):

sku_code (string, bắt buộc).

location_code (string, bắt buộc).

action (string, bắt buộc): Chỉ nhận giá trị INCREASE hoặc DECREASE.

quantity (integer, bắt buộc).

6. move_stock_between_locations
Mô tả: Thực hiện lệnh dịch chuyển nội bộ một số lượng hàng cụ thể từ kệ này sang kệ khác (Internal Transfer).

Tham số đầu vào (inputSchema):

sku_code (string, bắt buộc).

from_location (string, bắt buộc).

to_location (string, bắt buộc).

quantity (integer, bắt buộc).

7. adjust_inventory_for_reason
Mô tả: Điều chỉnh lệch tồn kho khi phát hiện hàng hư hỏng, mất mát sau khi kiểm kê (Stock Adjustment).

Tham số đầu vào (inputSchema):

sku_code (string, bắt buộc).

location_code (string, bắt buộc).

reason (string, bắt buộc): Lý do (ví dụ: DAMAGED, LOST, FOUND).

quantity (integer, bắt buộc): Số lượng chênh lệch.

🔍 LỚP 3: PHÂN HỆ KIỂM TRA ĐỒNG THỜI & LOGS (CONCURRENCY & MONITORING)
Nhóm công cụ cực kỳ quan trọng giúp bạn và AI Agent Debug lỗi Backend, kiểm tra nghẽn mạch hệ thống hoặc Race Condition.

8. check_redis_locks
Mô tả: Quét và kiểm tra các Khóa phân tán (Distributed Locks) đang tồn tại trên Redis của một SKU hoặc một Đơn hàng để tìm nguyên nhân bị treo API.

Tham số đầu vào (inputSchema):

resource_key (string, bắt buộc): Ký tự khóa cần tra (ví dụ: lock:sku:SKU-1060-6GB hoặc lock:order:123).

9. get_stock_movement_history
Mô tả: Truy vết toàn bộ lịch sử dịch chuyển (Audit Trail) của một mã hàng trong một khoảng thời gian để tìm nguyên nhân gây lệch số liệu.

Tham số đầu vào (inputSchema):

sku_code (string, bắt buộc).

limit_days (integer, tùy chọn): Số ngày muốn lùi lại để tra cứu (Mặc định là 7 ngày).

10. view_message_queue_status
Mô tả: Lấy số lượng tin nhắn đang bị nghẽn (Backlog) chưa xử lý kịp trong Message Broker (RabbitMQ/Kafka) của các hàng đợi đơn hàng.

Tham số đầu vào (inputSchema):

queue_name (string, bắt buộc): Tên hàng đợi (ví dụ: wms.order.process).

🚨 LỚP 4: PHÂN HỆ BÁO CÁO VÀ AN TOÀN HỆ THỐNG (ALERTS & REPORTS)
Giúp AI chủ động phát hiện rủi ro và đưa ra cảnh báo sớm cho bạn hoặc điều hành viên.

11. get_low_stock_report
Mô tả: Quét toàn bộ Database để xuất ra danh sách các mặt hàng có số lượng tồn kho khả dụng (Available Qty) chạm hoặc dưới mức an toàn (Safety Stock).

Tham số đầu vào (inputSchema): Không cần tham số đầu vào (Hoặc nhận threshold_qty nếu muốn tùy chỉnh).

12. create_system_alert
Mô tả: Đẩy một thông báo cảnh báo nghiêm trọng lên hệ thống giám sát hoặc ghi vào bảng system_alerts khi AI phát hiện ra bất thường (ví dụ: Phát hiện kho hết chỗ chứa, hoặc phát hiện lỗi lock hệ thống).

Tham số đầu vào (inputSchema):

alert_type (string, bắt buộc): Phân loại lỗi (CRITICAL, WARNING, INFO).

message (string, bắt buộc): Nội dung chi tiết của cảnh báo.

II. Phần nâng cao
1. Phân hệ Quản lý Đơn hàng & Đóng gói (Order Fulfillment & Packing Service)Trong 12 tool trước, chúng ta mới chỉ focus vào "Hàng hóa nằm trên kệ". Chúng ta đang thiếu hẳn công cụ để AI hiểu về "Đơn hàng của Khách".get_order_status_details (Tra cứu chi tiết đơn hàng):Input: order_id (Mã đơn hàng).Nhiệm vụ: Trả về trạng thái đơn (PENDING, PICKING, PACKED, SHIPPED), danh sách các SKU trong đơn và thông tin khách hàng.suggest_packing_box (Gợi ý thùng đóng gói tối ưu):Input: order_id.Nhiệm vụ: Tính toán tổng thể tích/khối lượng của các mặt hàng trong đơn, đối chiếu với danh mục thùng carton trong DB để gợi ý AI chọn size thùng nhỏ nhất $\rightarrow$ Tiết kiệm chi phí vận chuyển.
2. Phân hệ Lấy hàng thông minh (Smart Picking Service)Khi một đơn hàng được duyệt, thủ kho phải đi gom hàng từ các kệ. Đây là nơi thuật toán phát huy tác dụng.generate_picking_route (Tối ưu tuyến đường lấy hàng):Input: order_id hoặc danh sách sku_codes.Nhiệm vụ: Tìm ra các vị trí kệ đang chứa các SKU này, sau đó áp dụng thuật toán (như TSP - Traveling Salesperson) để sắp xếp thứ tự các kệ cần đến sao cho quãng đường thủ kho (hoặc robot) phải đi bộ trong kho là ngắn nhất.
3. Phân hệ Quản lý Đối tác & Nhà cung cấp (Procurement & Supplier Service)Hàng không tự nhiên sinh ra, nó đến từ các nhà cung cấp (Suppliers) thông qua các đơn mua hàng (Purchase Orders - PO).verify_incoming_po (Kiểm tra đơn nhập kho từ nhà cung cấp):Input: po_number (Mã đơn mua hàng).Nhiệm vụ: Đối chiếu danh sách hàng thực tế xe tải vừa chở đến xem có khớp với số lượng đã đặt mua trên hệ thống không, check xem có bị giao thiếu hoặc giao thừa không.
4. Phân hệ Quản lý Nhân sự & Phân quyền (User & Labor Management)Một hệ thống 10 microservices chắc chắn có phân quyền. AI cần biết "Ai đang làm gì" để trace log bảo mật hoặc điều phối công việc.assign_picking_task (Giao việc tự động):Input: task_id, user_id (Mã nhân viên).Nhiệm vụ: Giao một lệnh lấy hàng hoặc kiểm kho cho một nhân viên cụ thể đang rảnh tay trong ca trực.audit_user_permissions (Kiểm tra quyền hạn của User):Input: user_id, action_required (ví dụ: DELETE_STOCK).Nhiệm vụ: Check xem user này có đủ thẩm quyền để thực hiện các thao tác nhạy cảm không (Đề phòng trường hợp lỗi bảo mật).
5. Phân hệ Vận chuyển & Giao hàng (Shipping & Delivery Service)Sau khi đóng gói, hàng cần được bàn giao cho các đơn vị vận chuyển (3PL như GHTK, GHN, DHL...).create_shipping_label (Tạo vận đơn):Input: order_id, carrier_id (Mã nhà xe/đơn vị vận chuyển).Nhiệm vụ: Gọi API sang hệ thống của bên vận chuyển để lấy mã Tracking Number và sinh ra file nhãn dán (Shipping Label) để in ra dán lên thùng hàng.