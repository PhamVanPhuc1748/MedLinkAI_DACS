# Tổng Hợp Thuật Toán Và Công Thức Toán Học Huấn Luyện Mô Hình

Tài liệu này tổng hợp ngắn gọn pipeline huấn luyện trong dự án, tập trung vào bản đầy đủ ở:

- `src/backend/app/ai/huan_luyen.py`
- `src/backend/app/ai/mo_hinh_ai.py`
- `src/backend/app/ai/fuzzy_layer.py`
- `src/backend/app/ai/gcn_flow.py`

## 1. Bài toán

Dự án giải bài toán **dự đoán liên kết Thuốc - Bệnh** (Drug-Disease Link Prediction) trên đồ thị dị thể, sau đó chuyển sang đồ thị đồng nhất để lan truyền bằng GCN.

- Cạnh dương: cặp `(drug, disease)` đã biết có liên kết.
- Cạnh âm: cặp được sinh ngẫu nhiên nhưng không thuộc tập dương.

## 2. Chuẩn bị dữ liệu

1. Đọc ma trận đặc trưng thuốc và bệnh từ CSV.
2. Đọc danh sách cạnh dương từ `DrugDiseaseAssociationNumber.csv`.
3. Lọc index hợp lệ theo số lượng nút thực tế.
4. Chuẩn hoá đặc trưng (StandardScaler) nếu bật cấu hình.
5. Sinh negative samples theo tỉ lệ:

\[
|N| = \rho \cdot |P|
\]

Trong đó:

- \(P\): tập cạnh dương.
- \(N\): tập cạnh âm.
- \(\rho\): `negative-rate`.

6. Gộp dữ liệu:

\[
\mathcal D = P \cup N,\quad
y=
\begin{cases}
1, & (d,p)\in P\\
0, & (d,p)\in N
\end{cases}
\]

## 3. Chia K-Fold

Dùng `StratifiedKFold` để giữ cân bằng lớp giữa train/test cho từng fold:

\[
\mathcal D \rightarrow \{(\mathcal D^{(k)}_{train}, \mathcal D^{(k)}_{test})\}_{k=1}^{K}
\]

Lưu ý quan trọng trong code: đồ thị message-passing của mỗi fold chỉ xây từ **cạnh dương train** để tránh rò rỉ thông tin test.

## 4. Kiến trúc mô hình FuzzyGCN

## 4.1 Mã hoá đầu vào theo loại nút

Với đặc trưng đầu vào:

- \(x_d \in \mathbb{R}^{D_{drug}}\)
- \(x_p \in \mathbb{R}^{D_{disease}}\)

Mã hoá tuyến tính + fuzzy riêng:

\[
h_d^{(0)} = \text{Fuzzy}_{drug}(W_d x_d + b_d),\quad
h_p^{(0)} = \text{Fuzzy}_{disease}(W_p x_p + b_p)
\]

## 4.2 Fuzzy layer đa quy tắc (Gaussian + Tam giác)

Với mỗi chiều \(i\):

\[
m^{\text{gauss}}_i(x_i) = \exp\left(-\frac{(x_i-\mu_i)^2}{2\sigma_i^2}\right)
\]

\[
m^{\text{tri}}_i(x_i) = \max\left(0,\ 1-\frac{|x_i-\mu_i|}{\sigma_i}\right)
\]

\[
\alpha = \sigma(\alpha_0),\quad
m_i = \alpha m^{\text{gauss}}_i + (1-\alpha)m^{\text{tri}}_i
\]

\[
\text{Fuzzy}(x)_i = x_i \cdot m_i
\]

Trong đó \(\sigma_i\) được đảm bảo dương qua `softplus(log_sigma)`.

## 4.3 Trọng số cạnh

Trên đồ thị đồng nhất, trọng số cạnh dùng Gaussian RBF của cosine similarity:

\[
\cos_{ij} = \frac{h_i^\top h_j}{\|h_i\|\|h_j\|},\quad
w_{ij} = \exp\left(-\frac{(1-\cos_{ij})^2}{2}\right)
\]

## 4.4 Residual GCN + LayerNorm

Với lớp ẩn \(l=0,\dots,L-2\):

\[
\tilde h^{(l)} = \text{GCNConv}(h^{(l)}, E, w)
\]

\[
h^{(l+1)} = \text{LayerNorm}\left(\text{ELU}(\tilde h^{(l)}) + h^{(l)}\right)
\]

(kèm dropout trong huấn luyện).

Lớp cuối:

\[
h^{(L)} = \text{GCNConv}(h^{(L-1)}, E, w)
\]

## 4.5 Bộ giải mã cặp thuốc - bệnh (MLP)

Với embedding cuối của thuốc \(e_d\) và bệnh \(e_p\):

\[
z = [e_d \,\|\, e_p \,\|\, (e_d \odot e_p)]
\]

\[
s(d,p) = W_2\,\text{ELU}(W_1 z + b_1) + b_2
\]

\[
\hat y(d,p)=\sigma(s(d,p))
\]

Trong đó \(s(d,p)\) là **logit**.

## 5. Hàm mất mát huấn luyện

Code dùng loss kết hợp:

\[
\mathcal L = \mathcal L_{\text{BCE-LS}} + \lambda_{\text{rank}}\mathcal L_{\text{margin}}
\]

## 5.1 Label smoothing + BCEWithLogits

\[
\tilde y_i = (1-\varepsilon)y_i + \frac{\varepsilon}{2}
\]

\[
\mathcal L_{\text{BCE-LS}}
= -\frac{1}{n}\sum_{i=1}^n
\left[\tilde y_i\log \sigma(s_i) + (1-\tilde y_i)\log(1-\sigma(s_i))\right]
\]

## 5.2 Margin ranking loss

Lấy mẫu cặp dương/âm:

\[
\mathcal L_{\text{margin}}
= \mathbb{E}_{(+),(-)}
\left[\max(0,\ \gamma - s_+ + s_-)\right]
\]

Mục tiêu: đẩy \(s_+\) lớn hơn \(s_-\) ít nhất một biên \(\gamma\).

## 6. Tối ưu hoá

- Optimizer: **AdamW**.
- Gradient clipping:

\[
\|\nabla\|_2 \le \tau
\]

với \(\tau =\) `clip_grad`.

- LR scheduler: `ReduceLROnPlateau` theo AUC validation.
- Mixed precision (tuỳ chọn AMP).
- Early stopping theo AUC:
  - cải thiện khi `AUC > best_auc + min_delta`
  - dừng khi không cải thiện đủ `patience` epoch liên tiếp.

## 7. Chọn ngưỡng phân loại và đánh giá

Mỗi epoch:

1. Tính score train.
2. Quét ngưỡng \(t \in [0.2, 0.8]\) để tối đa F1 trên train.
3. Dùng ngưỡng tốt nhất đó để đánh giá test.

Các chỉ số báo cáo:

- AUC
- AUPR
- Accuracy
- Precision
- Recall
- F1
- MCC

Sau K fold, lấy trung bình:

\[
\bar m = \frac{1}{K}\sum_{k=1}^{K} m_k
\]

và lưu vào `kfold_metrics.json`.

## 8. Tóm tắt pipeline huấn luyện

1. Nạp dữ liệu + tiền xử lý.
2. Sinh cạnh âm và tạo nhãn.
3. Chia Stratified K-Fold.
4. Với mỗi fold:
   - Tạo đồ thị từ cạnh dương train.
   - Huấn luyện FuzzyGCN với loss kết hợp.
   - Tối ưu AdamW + scheduler + early stopping.
   - Lưu checkpoint tốt nhất theo AUC.
5. Tổng hợp metric trung bình toàn bộ fold.
