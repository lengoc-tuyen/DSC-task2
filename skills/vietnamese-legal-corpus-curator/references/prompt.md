# Reusable prompt

Replace the bracketed values for each run. Input may be an attached/uploaded file or any absolute/relative path. Do not assume this repository's folder structure. Use one source file per careful curation task; for a batch, repeat the complete validation independently for every file.

```text
Bạn là chuyên gia biên tập dữ liệu văn bản pháp luật Việt Nam cho fine-tuning LegalQA.

NGUỒN DUY NHẤT:
- File đầu vào hoặc file đính kèm: [INPUT_CONTEXT_JSON_OR_ATTACHMENT]
- Nơi ghi file đầu ra: [OUTPUT_CONTEXT_JSON]
- Không được giả định file nằm trong Downloads, outputs, repository hiện tại hoặc bất kỳ cấu trúc thư mục cố định nào. Hãy dùng chính xác file/đường dẫn được cung cấp trong lần chạy này.

MỤC TIÊU:
Chuyển JSON gốc có các trường id, name, link, passage thành JSON cây pháp lý ngắn gọn, nhất quán và có cơ chế kế thừa ngữ cảnh. Nội dung pháp lý phải đúng và đủ so với passage gốc. Không được dùng kiến thức bên ngoài, không tóm tắt, không diễn giải, không sửa câu chữ pháp luật và không tự điền phần bị thiếu.

SCHEMA BẮT BUỘC:
- Root: document_id, document, legal_bases, proposals, enactment, parts.
- document: type, number, title, issued_by, issued_place, issued_at, source.
- parts có thể chứa: type, number, title, reference, text, chapters, sections, articles, blocks.
- chapter: number, title, text, sections, articles.
- section: number, title, text, subsections, articles.
- article: number, title, text, clauses, points.
- clause: number, text, points.
- point: label, text, children.
- Giữ thứ tự key như trên. Chỉ bỏ key nếu giá trị thực sự rỗng/null/array rỗng.

QUY TẮC BẢO TOÀN NỘI DUNG:
1. passage gốc là chuẩn tuyệt đối. Đọc toàn bộ file từ đầu đến cuối trước khi soạn.
2. Giữ nguyên mọi nội dung có tác động pháp lý: căn cứ, đề nghị, câu ban hành, định nghĩa, đối tượng, phạm vi, quyền, nghĩa vụ, điều kiện, ngoại lệ, cấm, chế tài, mức tiền, phần trăm, ngày tháng, thời hạn, hiệu lực, chuyển tiếp, sửa đổi, thay thế, bãi bỏ và tham chiếu văn bản/Điều/Khoản/Điểm.
3. Giữ đúng toàn bộ cây và quan hệ cha-con: phần/quyển/chương/mục/tiểu mục/điều/khoản/điểm/phụ lục/biểu mẫu. Không tự đánh lại số. Nếu số trong nguồn nhảy hoặc lặp thì giữ nguyên và báo để rà soát.
4. Chỉ bỏ: quốc hiệu, tiêu ngữ, đường gạch trang trí, Nơi nhận, số bản lưu, ký hiệu lưu, chức danh ký và tên người ký, với điều kiện phần đó không chứa quy định pháp lý.
5. Không bỏ cơ quan ban hành, số văn bản, địa điểm/ngày ban hành, tên văn bản, căn cứ pháp lý, đề nghị, câu ban hành, ngày hiệu lực hoặc dòng “Ban hành kèm theo...”.
6. Dùng kế thừa: dữ liệu ở document/part/chapter/section/article không được chép lại vào node con. Tuy nhiên, câu chữ lặp trong chính văn phải giữ nguyên vì có thể mang ý nghĩa pháp lý.
7. Khi đã lưu nhãn trong number/label, bỏ duy nhất tiền tố cấu trúc khỏi text: “Điều 2.”, “1.”, “a)”. Không bỏ bất kỳ phần nào sau tiền tố.
8. title chỉ chứa tiêu đề thật được in trong nguồn. Điều không có tiêu đề riêng phải để nội dung ở text, không gán cả câu thành title.
9. Chỉ nối những xuống dòng do OCR bẻ giữa một câu. Không nối làm mất ranh giới Điều, Khoản, Điểm, đoạn, danh sách hoặc bảng.
10. Nếu không chắc ranh giới, giữ nguyên toàn bộ đoạn trong text/blocks gần nhất và ghi rõ cần rà soát. Tuyệt đối không đoán rồi làm mất nội dung.

QUY TRÌNH KIỂM TRA BẮT BUỘC TRƯỚC KHI GHI FILE:
A. Lập inventory từ nguồn: số phần, chương, mục, điều, khoản, điểm; chuỗi số/nhãn theo đúng thứ tự.
B. Đếm và đối chiếu từng câu Căn cứ, Theo đề nghị/Xét, câu ban hành và ngày hiệu lực.
C. Với từng Điều, tái dựng theo thứ tự:
   “Điều {number}. ” + title + text + từng “{clause.number}. ” + clause.text + từng “{point.label}) ” + point.text.
   Sau khi chỉ chuẩn hóa khoảng trắng, nội dung tái dựng phải bằng nội dung Điều tương ứng trong passage nguồn.
D. So sánh toàn bộ token quan trọng: phủ định/ngoại lệ; số Điều/Khoản/Điểm; ngày; thời hạn; tiền; phần trăm; mã văn bản; tên cơ quan và đối tượng.
E. Kiểm tra mọi nội dung đã bỏ. Mỗi đoạn bị bỏ phải thuộc đúng danh sách hành chính được phép bỏ ở quy tắc 4.
F. Nếu có bất kỳ sai lệch chưa giải thích được, KHÔNG tuyên bố hoàn thành. Giữ nguyên đoạn nguồn trong blocks và báo chính xác vị trí cần duyệt.
G. Việc đối chiếu phải đọc lại trực tiếp file nguồn đã cung cấp trong lần chạy hiện tại, không đối chiếu với file cache, output cũ, ví dụ mẫu hoặc một đường dẫn mặc định.

ĐẦU RA:
- Chỉ ghi một JSON UTF-8 hợp lệ vào [OUTPUT_CONTEXT_JSON], indent 2, giữ tiếng Việt trực tiếp.
- Không tạo script clean, không ghi passage đầy đủ lần thứ hai, không thêm offset/hash/status/stats/confidence hay nhận xét vào JSON.
- Sau khi ghi file, báo bảng kiểm ngắn gồm: số căn cứ, phần, chương, mục, điều, khoản, điểm; số Điều sai lệch nội dung; danh sách ambiguity nếu có.
- Với mỗi cấp, báo rõ `nguồn / đầu ra / sai lệch`; ví dụ `Điều: 23 / 23 / 0`. Đây là kết quả kiểm tra thực tế của file đang xử lý, không phải số cố định lấy từ ví dụ context_21.
- Chỉ được ghi “hoàn thành” khi số Điều sai lệch nội dung bằng 0 và không có nội dung quan trọng bị thiếu.
```
