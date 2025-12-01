# install_r_packages.R

# 1. QUAN TRỌNG: Thiết lập Repo Binary cho Debian Bookworm (Hệ điều hành của Streamlit)
# Việc này giúp tải file .deb đã đóng gói sẵn thay vì compile từ source.
options(repos = c(CRAN = "https://packagemanager.posit.co/cran/__linux__/bookworm/latest"))

# 2. Danh sách các thư viện cần thiết
packages <- c("ggplot2", "dplyr", "gtsummary", "survival", "survminer", "flextable")

# 3. Hàm kiểm tra và cài đặt
# Sử dụng Ncpus = 4 để cài song song nhiều gói cùng lúc (tăng tốc độ)
install_if_missing <- function(pkgs) {
  new_pkgs <- pkgs[!(pkgs %in% installed.packages()[,"Package"])]
  if(length(new_pkgs)) {
    message("Installing packages: ", paste(new_pkgs, collapse = ", "))
    install.packages(new_pkgs, Ncpus = 4) 
  }
}

install_if_missing(packages)
