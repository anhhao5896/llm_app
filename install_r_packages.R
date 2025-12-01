# install_r_packages.R

# 1. Dùng Repo Binary cho Debian Bookworm (Linux) -> Cài siêu nhanh
options(repos = c(CRAN = "https://packagemanager.posit.co/cran/__linux__/bookworm/latest"))

# 2. Thiết lập thư mục cài đặt cục bộ (tránh lỗi Permission)
lib_dir <- "r_libs"
if (!dir.exists(lib_dir)) dir.create(lib_dir)
.libPaths(c(lib_dir, .libPaths()))

# 3. Danh sách gói
packages <- c("ggplot2", "dplyr", "gtsummary", "survival", "survminer", "flextable")

# 4. Cài đặt thông minh (chỉ cài cái thiếu)
install_if_missing <- function(pkgs) {
  # Kiểm tra trong thư mục cục bộ
  installed_pkgs <- installed.packages(lib.loc = lib_dir)[,"Package"]
  new_pkgs <- pkgs[!(pkgs %in% installed_pkgs)]
  
  if(length(new_pkgs)) {
    message("Installing: ", paste(new_pkgs, collapse = ", "))
    # Cài vào thư mục r_libs, dùng 4 luồng CPU
    install.packages(new_pkgs, lib = lib_dir, Ncpus = 4)
  } else {
    message("All packages are ready.")
  }
}

install_if_missing(packages)
