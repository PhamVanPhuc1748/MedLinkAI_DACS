# Function Summary

## File: `extract_functions.py`

### Global Functions
- **`analyze_directory`**: (No docstring)

## File: `main.py`

### Global Functions
- **`_is_port_free`**: (No docstring)
- **`_find_free_port`**: Tìm cổng trống bắt đầu từ start.
- **`_kill_port`**: Dùng netstat + taskkill để giải phóng cổng trên Windows.
- **`_ensure_port_free`**: Kiểm tra cổng; nếu bận thì cố giải phóng hoặc tìm cổng mới.
- **`_run_db_setup`**: Chạy setup_database.main() trong thread nền và pipe log ra console.
- **`start_db_setup`**: Khởi chạy setup_database trong thread daemon — không block luồng chính.
- **`_run_api`**: (No docstring)
- **`start_api`**: (No docstring)
- **`start_streamlit`**: Khởi động Streamlit. Mặc định dùng app_modern.py; truyền classic=True để dùng UI cũ.
- **`parse_args`**: (No docstring)

## File: `src\backend\app\database.py`

### Global Functions
- **`_get_data_source`**: (No docstring)
- **`_load_manual_db_url`**: (No docstring)
- **`_build_engine`**: (No docstring)
- **`_try_connect`**: (No docstring)
- **`migrate_add_missing_columns`**: (No docstring)
- **`init_db`**: (No docstring)
- **`_sync_json_store`**: (No docstring)
- **`_start_json_realtime_sync`**: (No docstring)
- **`get_db`**: (No docstring)

## File: `src\backend\app\models.py`

### Classes
#### Class: `Base`
> Base class for all ORM models.


#### Class: `User`

#### Class: `Drug`

#### Class: `Disease`

#### Class: `DrugDiseaseLink`

#### Class: `Protein`

#### Class: `DrugProteinLink`

#### Class: `ProteinDiseaseLink`

#### Class: `PredictionHistory`

#### Class: `_ThuocBase`
> Lưu danh sách thuốc của một dataset cụ thể.


#### Class: `ThuocB`
> Danh sách thuốc – B-dataset.


#### Class: `ThuocC`
> Danh sách thuốc – C-dataset.


#### Class: `ThuocF`
> Danh sách thuốc – F-dataset.


#### Class: `_BenhBase`
> Lưu danh sách bệnh của một dataset cụ thể.


#### Class: `BenhB`
> Danh sách bệnh – B-dataset.


#### Class: `BenhC`
> Danh sách bệnh – C-dataset.


#### Class: `BenhF`
> Danh sách bệnh – F-dataset.


#### Class: `_ProteinBase`
> Lưu danh sách protein của một dataset cụ thể.


#### Class: `ProteinB`
> Danh sách protein – B-dataset.


#### Class: `ProteinC`
> Danh sách protein – C-dataset.


#### Class: `ProteinF`
> Danh sách protein – F-dataset.


#### Class: `_LienKetBase`
> Lưu liên kết thuốc–bệnh của một dataset cụ thể.


#### Class: `LienKetB`
> Liên kết thuốc–bệnh – B-dataset.


#### Class: `LienKetC`
> Liên kết thuốc–bệnh – C-dataset.


#### Class: `LienKetF`
> Liên kết thuốc–bệnh – F-dataset.


## File: `src\backend\app\schemas.py`

### Classes
#### Class: `LoginRequest`

#### Class: `LoginResponse`

#### Class: `RegisterRequest`

#### Class: `ForgotPasswordRequest`

#### Class: `ResetPasswordRequest`

#### Class: `PredictRequest`

#### Class: `PredictionItem`

#### Class: `PredictResponse`

#### Class: `HistoryItem`

#### Class: `DrugIn`

#### Class: `DiseaseIn`

#### Class: `LinkIn`

#### Class: `StatsResponse`

#### Class: `ModelCompareRequest`

#### Class: `AdminRecalcRequest`

#### Class: `SeedDatasetRequest`

#### Class: `UserRoleUpdate`
> Payload để Admin cập nhật role của một user.


#### Class: `UserItem`
> Thông tin tóm tắt một user dùng trong trang Admin.


## File: `src\backend\app\security.py`

### Global Functions
- **`_is_legacy_sha256`**: Hash SHA-256 thuần: dài đúng 64 ký tự hex, KHÔNG bắt đầu bằng '$'.
- **`hash_password`**: Băm mật khẩu bằng bcrypt (nếu có passlib) hoặc sha256 (fallback).
- **`verify_password`**: Xác thực mật khẩu với tương thích ngược:
- **`create_token`**: (No docstring)

### Classes
#### Class: `AuthUser`

## File: `src\backend\app\__init__.py`

### Global Functions
- **`create_app`**: (No docstring)

## File: `src\backend\app\ai\fuzzy_layer.py`

### Classes
#### Class: `LopFuzzy`
> Tầng Fuzzy đa kênh, đa quy tắc (Gaussian + Triangular membership).

- **`__init__`**: (No docstring)
- **`forward`**: Áp dụng hàm thành viên Fuzzy lên từng chiều của x.

## File: `src\backend\app\ai\gcn_flow.py`

### Global Functions
- **`tao_cac_lop_gcn`**: Trả về (cac_lop_gcn, cac_layer_norm).
- **`tinh_trong_so_canh`**: Gaussian RBF trên cosine similarity: w_ij = exp(-(1 - cos_ij)² / 2).
- **`truyen_qua_cac_lop_gcn`**: Chạy qua toàn bộ các lớp GCN với residual connection + LayerNorm.
- **`chay_forward_gcn`**: Luồng forward GCN tổng hợp: tính trọng số cạnh → truyền qua các lớp GCN.

### Classes
#### Class: `GiaiMaMLPN`
> Bộ giải mã MLP: z = [e_d || e_p || e_d⊙e_p] → Linear → ELU → Linear → score.

- **`__init__`**: (No docstring)
- **`forward`**: (No docstring)

## File: `src\backend\app\ai\gnn_algorithm.py`

### Global Functions
- **`chuyen_sang_dong_nhat`**: Mã hóa từng loại nút qua Linear + LopFuzzy riêng, chuyển về đồ thị đồng nhất.
- **`tinh_trong_so_canh`**: Tính trọng số cạnh bằng Gaussian RBF trên cosine similarity.
- **`truyen_qua_cac_lop_gcn`**: Residual GCN: h^(l+1) = LayerNorm( ELU(GCN(h^(l))) + h^(l) ).

## File: `src\backend\app\ai\huan_luyen.py`

### Global Functions
- **`dat_seed`**: Đặt seed toàn cục để đảm bảo kết quả huấn luyện tái lập được (reproducibility).
- **`doc_ma_tran`**: Đọc file CSV đặc trưng và trả về ma trận numpy float32.
- **`doc_ma_tran_optional`**: Doc file CSV neu ton tai, tra ve None neu khong tim thay.
- **`ghep_feature_thuoc`**: Ghep DrugFingerprint + DrugGIP + Drug_mol2vec thanh 1 vector per drug.
- **`ghep_feature_benh`**: Ghep DiseaseFeature + DiseaseGIP + DiseasePS thanh 1 vector per disease.
- **`doc_lien_ket`**: Đọc file liên kết thuốc-bệnh (cạnh dương của đồ thị).
- **`can_chinh_hang`**: Tự động căn chỉnh ma trận sao cho số hàng = số thực thể.
- **`chuan_hoa_dac_trung`**: Chuẩn hóa đặc trưng thuốc và bệnh bằng StandardScaler.
- **`tao_do_thi`**: Tạo đồ thị HeteroData (dị đồng nhất) cho PyTorch Geometric.
- **`tao_canh_am`**: Sinh cạnh âm (negative edges) bằng phương pháp random negative sampling.
- **`giai_ma_diem`**: Tinh logit. Neu truyen mo_hinh thi dung MLP decoder (tot hon), khong thi dung dot product.
- **`_tinh_logits`**: Dung bo_giai_ma (MLP) neu co, fallback ve dot-product.
- **`tinh_loss_ket_hop`**: Hàm mất mát kết hợp: BCE với Label Smoothing + Margin Ranking Loss.
- **`tim_nguong_toi_uu_f1`**: Tìm ngưỡng phân loại tối ưu theo F1-score trên tập train.
- **`tinh_chi_so`**: Tính đầy đủ các chỉ số đánh giá mô hình phân loại nhị phân.
- **`huan_luyen_1_fold`**: Huấn luyện và đánh giá FuzzyGCN trên 1 fold của K-Fold cross-validation.
- **`parse_args`**: Đọc tham số dòng lệnh cho huấn luyện FuzzyGCN.
- **`_huan_luyen_mot_dataset`**: Huấn luyện đầy đủ K-Fold cho 1 dataset, lưu trọng số và kết quả vào thư mục weights/.
- **`_chay_auto_tune`**: Chạy auto-tune sau khi training bình thường hoàn tất.
- **`main`**: Điểm vào chính: parse args → train → (nếu --auto-tune) tự động tìm thông số tốt hơn.

### Classes
#### Class: `CauHinh`
> Tất cả siêu tham số điều khiển quá trình huấn luyện FuzzyGCN.


## File: `src\backend\app\ai\inference_service.py`

### Global Functions
- **`_translate_disease`**: Dịch tên bệnh sang tiếng Việt nếu là mã OMIM (D102100...).
- **`_project_root`**: (No docstring)
- **`_dataset_dir`**: (No docstring)
- **`_normalize`**: (No docstring)
- **`load_drug_table`**: (No docstring)
- **`load_disease_table`**: (No docstring)
- **`load_disease_feature_matrix`**: Đọc đặc trưng bệnh, loại cột tên bệnh rồi mới ép kiểu số.
- **`load_links`**: (No docstring)
- **`load_protein_table`**: (No docstring)
- **`load_drug_protein_links`**: (No docstring)
- **`load_protein_disease_links`**: (No docstring)
- **`infer_feature_dims`**: Suy ra kích thước đặc trưng đầu vào từ file CSV.
- **`infer_arch_from_weights`**: Suy ra toàn bộ siêu tham số kiến trúc từ file .pth để tránh mismatch.
- **`_find_best_weights`**: Tìm file trọng số tốt nhất cho dataset theo AUC trong kfold_metrics.json.
- **`get_model`**: Tải mô hình FuzzyGCN đã được huấn luyện từ file trọng số đúng theo dataset.
- **`_build_full_graph`**: Xây dựng HeteroData đầy đủ cho toàn bộ dataset để chạy GNN inference thật.
- **`_get_full_embeddings`**: Chạy GNN forward pass trên toàn bộ đồ thị để lấy embedding của mọi nút.
- **`_predict_all_diseases_for_drug`**: Dự đoán xác suất liên kết thật cho 1 thuốc với tất cả bệnh bằng GNN.
- **`predict_diseases_by_drug_name`**: (No docstring)
- **`predict_drugs_by_disease_name`**: (No docstring)
- **`evaluate_custom_model`**: Đánh giá model .pth tùy chọn trên toàn bộ dataset.
- **`_build_full_graph`**: Bản override sạch để tránh ép cột tên bệnh sang float.
- **`inspect_model_pth`**: (No docstring)

## File: `src\backend\app\ai\model_factory.py`

### Global Functions
- **`khoi_tao_mo_hinh_gnn`**: (No docstring)

## File: `src\backend\app\ai\mo_hinh_ai.py`

### Classes
#### Class: `FuzzyGCN`
> Mô hình FuzzyGCN cho bài toán dự đoán liên kết thuốc-bệnh.

- **`__init__`**: Khởi tạo kiến trúc FuzzyGCN.
- **`_chuyen_sang_dong_nhat`**: (No docstring)
- **`forward`**: Chuyển HeteroData qua toàn bộ pipeline (mã hóa + GCN), trả về embedding.
- **`tinh_diem`**: Tính logit score cho các cặp (thuốc, bệnh) qua bộ giải mã MLP.
- **`tai_trong_so`**: Tải trọng số đã huấn luyện từ file checkpoint và chuyển sang eval mode.
- **`du_doan_top_k`**: [LEGACY FALLBACK] Hàm này chỉ dùng khi inference_service không thể build đồ thị.

## File: `src\backend\app\api\routes.py`

### Global Functions
- **`_routes_project_root`**: (No docstring)
- **`_send_reset_email`**: (No docstring)
- **`_auth_from_header`**: (No docstring)
- **`get_current_user`**: (No docstring)
- **`require_admin`**: (No docstring)
- **`require_researcher`**: Cho phép researcher và admin; từ chối guest và user thường.
- **`_db_auth_enabled`**: (No docstring)
- **`_user_to_dict`**: (No docstring)
- **`_get_auth_user_by_username`**: (No docstring)
- **`_get_auth_user_by_username_and_email`**: (No docstring)
- **`_auth_user_exists`**: (No docstring)
- **`_auth_email_exists`**: (No docstring)
- **`_auth_create_user`**: (No docstring)
- **`_auth_update_password`**: (No docstring)
- **`health`**: (No docstring)
- **`db_status`**: Trả về trạng thái kết nối database chi tiết.
- **`admin_db_setup`**: Chạy setup_database.py để tự động bật SQL Server, tạo DB, tạo bảng.
- **`login`**: (No docstring)
- **`register`**: (No docstring)
- **`forgot_password`**: (No docstring)
- **`reset_password`**: (No docstring)
- **`predict_drug_to_disease`**: (No docstring)
- **`predict_disease_to_drug`**: (No docstring)
- **`history`**: (No docstring)
- **`list_drugs`**: (No docstring)
- **`list_diseases`**: (No docstring)
- **`list_proteins`**: (No docstring)
- **`get_protein_links`**: (No docstring)
- **`list_links`**: (No docstring)
- **`user_stats`**: (No docstring)
- **`admin_list_users`**: Lấy danh sách tất cả user (chỉ Admin).
- **`admin_update_user_role`**: Cập nhật role cho một user (chỉ Admin). Không thể gán role 'guest'.
- **`admin_stats`**: (No docstring)
- **`admin_prediction_direction_stats`**: (No docstring)
- **`admin_list_predictions`**: (No docstring)
- **`admin_create_drug`**: (No docstring)
- **`admin_create_disease`**: (No docstring)
- **`admin_delete_drug`**: (No docstring)
- **`admin_delete_disease`**: (No docstring)
- **`admin_create_link`**: (No docstring)
- **`admin_delete_link`**: (No docstring)
- **`admin_seed_dataset`**: Tai dataset tu CSV goc -> ghi vao JSON store.
- **`admin_dataset_preview`**: (No docstring)
- **`_find_metrics_files`**: (No docstring)
- **`_extract_metrics`**: (No docstring)
- **`model_metrics`**: (No docstring)
- **`inspect_model`**: (No docstring)
- **`evaluate_model`**: Evaluate a custom .pth model on the chosen dataset.
- **`model_compare`**: (No docstring)
- **`admin_recalculate_metrics`**: (No docstring)

## File: `src\data\assets_config.py`

### Global Functions
- **`_encode_image`**: Đọc file ảnh → chuỗi CSS url('data:...').
- **`get_bg_css`**: Trả về CSS background-image cho landing page.

## File: `src\data\data_source_status.py`

### Classes
#### Class: `DataSourceStatus`
> Singleton tracking the active data source.

- **`__init__`**: (No docstring)
- **`set_db_connected`**: Set the current source to a connected database or reset to JSON.
- **`set_json_only`**: Set the current source to JSON-only mode.
- **`update_json_counts`**: Update JSON record counts after synchronization.
- **`current_source`**: (No docstring)
- **`is_db_connected`**: (No docstring)
- **`is_json_synced`**: (No docstring)
- **`report`**: Log the full data-source status.
- **`_short_summary`**: (No docstring)

## File: `src\data\disease_translator.py`

### Global Functions
- **`init_translations`**: (No docstring)
- **`translate_disease`**: Trả về tên Tiếng Việt của bệnh nếu có, nếu không thì giữ nguyên tên gốc.
- **`get_display_name`**: Trả về chuỗi hiển thị kết hợp gốc và dịch (ví dụ: 'anxiety disorders (Rối loạn lo âu)').

## File: `src\data\export_to_json.py`

### Global Functions
- **`_export_users`**: (No docstring)
- **`_export_drugs`**: (No docstring)
- **`_export_diseases`**: (No docstring)
- **`_export_proteins`**: (No docstring)
- **`_export_drug_disease_links`**: (No docstring)
- **`_export_drug_protein_links`**: (No docstring)
- **`_export_protein_disease_links`**: (No docstring)
- **`_export_prediction_history`**: (No docstring)
- **`_export_dataset_tables`**: (No docstring)
- **`export_all`**: (No docstring)
- **`_parse`**: (No docstring)

## File: `src\data\import_history_to_sql.py`

### Global Functions
- **`init_db`**: (No docstring)
- **`load_json_to_sql`**: (No docstring)

## File: `src\data\json_repo.py`

### Global Functions
- **`_hash`**: (No docstring)
- **`bootstrap`**: Dam bao tai khoan mac dinh ton tai va co password_hash.
- **`get_user_by_username`**: (No docstring)
- **`get_user_by_username_and_email`**: (No docstring)
- **`user_exists`**: (No docstring)
- **`email_exists`**: (No docstring)
- **`create_user`**: (No docstring)
- **`update_user_password`**: (No docstring)
- **`add_prediction`**: (No docstring)
- **`list_predictions_by_user`**: (No docstring)
- **`list_all_predictions`**: (No docstring)
- **`list_drugs`**: (No docstring)
- **`upsert_drug`**: (No docstring)
- **`delete_drug`**: (No docstring)
- **`list_diseases`**: (No docstring)
- **`upsert_disease`**: (No docstring)
- **`delete_disease`**: (No docstring)
- **`list_proteins`**: (No docstring)
- **`get_protein_links`**: (No docstring)
- **`list_links`**: (No docstring)
- **`create_link`**: (No docstring)
- **`delete_link`**: (No docstring)
- **`user_stats`**: (No docstring)
- **`admin_stats`**: (No docstring)
- **`prediction_direction_stats`**: (No docstring)
- **`dataset_preview`**: (No docstring)

## File: `src\data\json_store.py`

### Global Functions
- **`_get_data_source`**: (No docstring)

### Classes
#### Class: `JsonTable`
> Thread-safe, in-memory + file-backed JSON table.

- **`__init__`**: (No docstring)
- **`_load`**: (No docstring)
- **`_save`**: (No docstring)
- **`all`**: (No docstring)
- **`count`**: (No docstring)
- **`get`**: (No docstring)
- **`find`**: (No docstring)
- **`find_one`**: (No docstring)
- **`upsert`**: (No docstring)
- **`delete`**: (No docstring)
- **`replace_all`**: (No docstring)
- **`reload`**: (No docstring)
- **`__repr__`**: (No docstring)

#### Class: `JsonStore`
> Central registry for all JSON-backed tables.

- **`__init__`**: (No docstring)
- **`table`**: (No docstring)
- **`reload_all`**: (No docstring)
- **`summary`**: (No docstring)
- **`mark_internal_write`**: (No docstring)
- **`start_realtime_sync`**: (No docstring)
- **`sync_all_to_db`**: (No docstring)
- **`sync_table_to_db`**: (No docstring)
- **`_watch_loop`**: (No docstring)
- **`_file_token`**: (No docstring)
- **`_normalize_bool`**: (No docstring)
- **`_normalize_datetime`**: (No docstring)
- **`_normalize_record`**: (No docstring)
- **`_db_runtime`**: (No docstring)
- **`_db_sync_enabled`**: (No docstring)
- **`__repr__`**: (No docstring)

## File: `src\data\omim_viet_dict.py`

### Global Functions
- **`get_viet_name`**: Trả về tên Tiếng Việt của mã bệnh OMIM.
- **`get_en_name`**: Trả về tên tiếng Anh của mã OMIM.
- **`translate_disease_name`**: Dịch tên bệnh sang tiếng Việt.

## File: `src\frontend\app_modern.py`

### Global Functions
- **`_html_iframe`**: Render HTML string bằng st.iframe thông qua file tạm (Streamlit 1.57+).
- **`_restore_session_from_url`**: Khôi phục session từ URL query params sau khi F5.
- **`_role`**: Lấy vai trò hiện tại từ session_state.
- **`_can`**: Kiểm tra người dùng có đủ quyền tối thiểu không.
- **`_is_logged_in`**: Giả lập trạng thái đăng nhập: guest = chưa đăng nhập.
- **`_history_cache_key`**: (No docstring)
- **`_clear_prediction_history_cache`**: (No docstring)
- **`_history_client`**: (No docstring)
- **`_load_prediction_history`**: (No docstring)
- **`_format_history_rows`**: (No docstring)
- **`render_login_dialog`**: (No docstring)
- **`render_sidebar`**: Vẽ sidebar với option_menu (streamlit-option-menu).
- **`render_intro_page`**: Trang tổng quan về hệ thống FuzzyGCN.
- **`render_catalog_page`**: Trang tra cứu danh mục thuốc và bệnh.
- **`_smiles_to_svg`**: Dùng rdkit tạo SVG từ SMILES. Trả '' nếu thất bại.
- **`_smiles_to_3d_mol`**: (No docstring)
- **`_build_mol_html`**: Tạo HTML hiển thị cấu trúc phân tử cho nhiều thuốc.
- **`_build_bipartite_html`**: Tạo bipartite diagram thuần HTML/SVG/JS:
- **`_build_prediction_network`**: Tạo đồ thị Pyvis kết quả dự đoán và trả về chuỗi HTML.
- **`render_prediction_page`**: Trạm Dự Đoán AI — FuzzyGCN.
- **`render_network_page`**: Render đồ thị sinh học 15 nodes bằng pyvis:
- **`render_review_page`**: Giao diện cho Expert duyệt các liên kết mới được AI tìm ra.
- **`_data_root`**: (No docstring)
- **`_load_json_records`**: (No docstring)
- **`_save_json_records`**: (No docstring)
- **`_flatten_history_rows`**: (No docstring)
- **`_metrics_table_from_weights`**: (No docstring)
- **`_db_schema_groups`**: (No docstring)
- **`render_config_page`**: Trang cau hinh mo hinh va xem metrics chi tiet (chi Admin).
- **`_load_kfold_metrics`**: Đọc kfold_metrics.json của cả 3 dataset. Trả về dict {label: data}.
- **`render_compare_page`**: Trang So Sánh Model — expert/admin đều xem được.
- **`render_account_management_page`**: Trang quan ly tai khoan va lich su du doan cho Admin.
- **`render_landing_page`**: Render trang chủ công khai với form đăng nhập và chọn demo role.
- **`main`**: Hàm điều phối chính — routing theo role và menu.

## File: `src\frontend\app\state.py`

### Global Functions
- **`clear_auth_state`**: (No docstring)
- **`is_authenticated`**: Trả về True nếu đã đăng nhập (có token thật) hoặc đang ở chế độ khách (role=guest).
- **`is_guest`**: (No docstring)
- **`current_role`**: (No docstring)

## File: `src\frontend\app\pages\admin.py`

### Global Functions
- **`_flat_mean`**: (No docstring)
- **`_flat_std`**: (No docstring)
- **`render_admin_console`**: (No docstring)

## File: `src\frontend\app\pages\auth.py`

### Global Functions
- **`render_login`**: (No docstring)

## File: `src\frontend\app\pages\landing.py`

### Global Functions
- **`_landing_css`**: (No docstring)
- **`_retrigger_js`**: (No docstring)
- **`_render_navbar`**: (No docstring)
- **`_render_hero_centered`**: Hero section căn giữa với title, mô tả, stats và CTA buttons trong hero.
- **`_render_hero_split`**: Hero 2 cột: trái = auth card, phải = mô tả tính năng.
- **`_render_features`**: (No docstring)
- **`_render_how_to_use`**: (No docstring)
- **`_render_cta_banner`**: (No docstring)
- **`_render_feedback_section`**: (No docstring)
- **`_render_contact_section`**: (No docstring)
- **`_render_footer`**: (No docstring)
- **`_auth_modal`**: Cửa sổ popup đăng nhập / đăng ký (mở từ navbar).
- **`_render_forgot_password`**: Form quên mật khẩu — OTP qua email.
- **`render_landing`**: Render toàn bộ trang chủ public (chưa đăng nhập).

## File: `src\frontend\app\pages\user.py`

### Global Functions
- **`_load_dropdown_values`**: (No docstring)
- **`_clean_filename`**: (No docstring)
- **`_render_molecule_preview`**: (No docstring)
- **`_render_molecule_download`**: (No docstring)
- **`_build_network_html`**: Return HTML: drug cards | SVG bezier connectors | disease cards.
- **`_build_dis_network_html`**: Return HTML: disease cards | SVG bezier connectors | drug cards. (Disease → Drug)
- **`_build_protein_network_html`**: Return HTML: protein cards | SVG bezier | drug or disease cards.
- **`_render_stats_group`**: Hiển thị nhóm thống kê: Thuốc / Bệnh / Protein / Liên kết trong database.
- **`render_user_workspace`**: (No docstring)

## File: `src\frontend\app\services\api_client.py`

### Classes
#### Class: `ApiError`
- **`__init__`**: (No docstring)

#### Class: `ApiClient`
- **`__init__`**: (No docstring)
- **`_request`**: (No docstring)
- **`health`**: (No docstring)
- **`login`**: (No docstring)
- **`register`**: (No docstring)
- **`forgot_password`**: (No docstring)
- **`reset_password`**: (No docstring)
- **`predict_drug_to_disease`**: (No docstring)
- **`predict_disease_to_drug`**: (No docstring)
- **`history`**: (No docstring)
- **`list_drugs`**: (No docstring)
- **`list_diseases`**: (No docstring)
- **`list_proteins`**: (No docstring)
- **`get_protein_links`**: (No docstring)
- **`list_links`**: (No docstring)
- **`stats`**: (No docstring)
- **`model_metrics`**: (No docstring)
- **`model_compare`**: (No docstring)
- **`admin_recalculate_metrics`**: (No docstring)
- **`admin_seed_dataset`**: (No docstring)
- **`admin_dataset_preview`**: (No docstring)
- **`admin_stats`**: (No docstring)
- **`admin_prediction_direction_stats`**: (No docstring)
- **`admin_predictions`**: (No docstring)
- **`admin_save_drug`**: (No docstring)
- **`admin_save_disease`**: (No docstring)
- **`admin_save_link`**: (No docstring)
- **`db_status`**: Kiểm tra trạng thái kết nối database.
- **`admin_db_setup`**: Chạy setup_database.py để tự động kết nối SQL Server (Admin only).
- **`evaluate_model`**: Upload và đánh giá model .pth tùy chọn.
- **`inspect_model`**: Kiểm tra cấu trúc file .pth.

## File: `src\frontend\app\ui\components.py`

### Global Functions
- **`_translate_omim`**: Dịch mã OMIM (D102100) sang tên Tiếng Việt để hiển thị trong bảng kết quả.
- **`card_open`**: (No docstring)
- **`card_close`**: (No docstring)
- **`show_result_table`**: (No docstring)
- **`_render_group_table`**: Render một nhóm kết quả (điều trị hoặc cảnh báo) vào bảng HTML.
- **`show_split_result_table`**: Hiển thị kết quả dự đoán dưới dạng 2 cột song song:
- **`show_history_table`**: (No docstring)
- **`show_metric_row`**: (No docstring)

## File: `src\frontend\app\ui\theme.py`

### Global Functions
- **`_get_theme_vars`**: (No docstring)
- **`apply_theme`**: (No docstring)
- **`render_hero`**: (No docstring)

## File: `src\scripts\database\cap_nhat_dtb.py`

### Global Functions
- **`_normalize`**: (No docstring)
- **`_read_drug_df`**: (No docstring)
- **`_read_disease_df`**: (No docstring)
- **`_read_protein_df`**: (No docstring)
- **`_read_link_df`**: (No docstring)
- **`rename_tables`**: (No docstring)
- **`drop_old_dataset_tables`**: (No docstring)
- **`create_tables`**: (No docstring)
- **`seed_dataset`**: (No docstring)
- **`seed_all`**: (No docstring)
- **`print_stats`**: (No docstring)

## File: `src\scripts\database\check_db.py`

### Global Functions
- **`_build_engine`**: (No docstring)
- **`_ping`**: Trả về (ok, message).
- **`check_and_connect`**: Thử kết nối primary_url (SQL Server).
- **`_parse_args`**: (No docstring)

## File: `src\scripts\database\seed_all_datasets.py`

### Global Functions
- **`load_drug_csv`**: (No docstring)
- **`load_disease_csv`**: (No docstring)
- **`load_links_csv`**: (No docstring)
- **`load_protein_csv`**: (No docstring)
- **`load_drug_protein_csv`**: (No docstring)
- **`load_protein_disease_csv`**: (No docstring)
- **`seed_dataset_tables`**: Xóa và nạp lại toàn bộ dữ liệu cho dataset này trong bảng dataset_*.
- **`upsert_main_tables`**: Gộp thuốc/bệnh/protein từ tất cả dataset và upsert vào bảng chính.
- **`main`**: (No docstring)

## File: `src\scripts\database\seed_sqlserver.py`

### Global Functions
- **`load_drug_df`**: (No docstring)
- **`load_disease_df`**: (No docstring)
- **`load_links_df`**: (No docstring)
- **`build_merged_data`**: Trả về (drugs_merged, diseases_merged, links_merged)
- **`seed_all`**: (No docstring)
- **`main`**: (No docstring)
- **`_normalize`**: (No docstring)
- **`load_drug_table`**: (No docstring)
- **`load_disease_table`**: (No docstring)
- **`load_links`**: (No docstring)
- **`seed_users`**: (No docstring)
- **`seed_drugs`**: (No docstring)
- **`seed_diseases`**: (No docstring)
- **`seed_links`**: (No docstring)
- **`run`**: (No docstring)
- **`main`**: (No docstring)

## File: `src\scripts\database\setup_database.py`

### Global Functions
- **`ok`**: (No docstring)
- **`warn`**: (No docstring)
- **`err`**: (No docstring)
- **`info`**: (No docstring)
- **`step`**: (No docstring)
- **`_get_service_state`**: Trả về 'Running', 'Stopped', hoặc None nếu service không tồn tại.
- **`start_sql_service`**: Tìm và bật dịch vụ SQL Server.
- **`_detect_instance`**: Xác định instance name từ service name.
- **`connect_sql_server`**: Kết nối SQL Server (master DB), trả về connection hoặc None.
- **`create_database`**: Tạo database nếu chưa tồn tại.
- **`create_tables`**: Tạo toàn bộ bảng từ ORM models.py.
- **`_hash_password`**: SHA-256 hash đơn giản (giống security.py).
- **`seed_default_accounts`**: Tạo tài khoản admin và user mặc định nếu chưa có.
- **`print_next_steps`**: (No docstring)
- **`main`**: (No docstring)

### Classes
#### Class: `C`

## File: `src\training\auto_tune.py`

### Global Functions
- **`_lay_mau_ngau_nhien`**: Lấy ngẫu nhiên 1 bộ thông số từ không gian tìm kiếm.
- **`_perturbation`**: Tạo bộ thông số mới bằng cách nhiễu nhỏ xung quanh best_params.
- **`_tao_cau_hinh`**: Tạo CauHinh mới từ base + params override.
- **`_chay_kfold_nhanh`**: Chạy K-Fold rút gọn (chỉ dùng so_fold_thu fold đầu) để ước lượng nhanh.
- **`_doc_auc_goc`**: Đọc AUC gốc từ weights/<dataset>/kfold_metrics.json.
- **`_luu_lich_su`**: Lưu thông số và kết quả trial vào file lịch sử.
- **`_luu_tong_ket`**: Lưu file tổng kết tất cả trials của 1 dataset.
- **`tu_dong_chinh_thong_so`**: Tự động tìm kiếm thông số huấn luyện tốt hơn baseline.
- **`_retrain_voi_thong_so_tot_nhat`**: Retrain đầy đủ K-Fold với thông số tốt nhất tìm được từ auto-tune.
- **`main`**: Điểm vào chính của tool auto-tune.

## File: `src\training\train_logger.py`

### Global Functions
- **`_now_str`**: (No docstring)
- **`_run_id`**: (No docstring)
- **`_env_info`**: (No docstring)
- **`_calc_stats`**: Tính mean và std cho từng metric qua tất cả fold.
- **`_csv_header`**: (No docstring)
- **`load_runs`**: Đọc toàn bộ lịch sử huấn luyện của 1 dataset từ runs.jsonl.
- **`load_summary`**: Đọc bảng tổng hợp best run của mỗi dataset.
- **`_safe_print`**: In văn bản ra console, bỏ qua lỗi encoding trên Windows.
- **`print_leaderboard`**: In bảng xếp hạng AUC tốt nhất của từng dataset.

### Classes
#### Class: `TrainRecord`

#### Class: `TrainLogger`
> Logger tự động ghi lại mọi lần chạy huấn luyện.

- **`__init__`**: (No docstring)
- **`begin`**: Điền thông tin từ CauHinh dataclass.
- **`begin_from_params`**: Điền thông tin từ params dict (dùng trong auto_tune).
- **`end`**: Ghi kết quả sau khi train xong, lưu file.
- **`_write_jsonl`**: (No docstring)
- **`_write_csv`**: (No docstring)
- **`_update_summary`**: (No docstring)
- **`_print_summary`**: (No docstring)

