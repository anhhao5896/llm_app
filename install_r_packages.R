# 1. Cấu hình Repo Binary (Debian Bookworm) để cài siêu tốc
options(repos = c(CRAN = "https://packagemanager.posit.co/cran/__linux__/bookworm/latest"))

# 2. Đảm bảo R nhận diện thư mục cục bộ (dù đã có .Rprofile, khai báo lại cho chắc chắn)
lib_dir <- "r_libs"
if (!dir.exists(lib_dir)) dir.create(lib_dir)
.libPaths(c(lib_dir, .libPaths()))

# 3. Danh sách gói cần cài
packages <- c("ggplot2", "dplyr", "gtsummary", "survival", "survminer", "flextable")

# 4. Hàm cài đặt an toàn
install_if_missing <- function(pkgs) {
  # Chỉ cài những gói chưa có trong thư mục r_libs
  new_pkgs <- pkgs[!(pkgs %in% installed.packages(lib.loc = lib_dir)[,"Package"])]
  
  if(length(new_pkgs)) {
    message("Installing packages to local dir: ", lib_dir)
    # QUAN TRỌNG: Tham số 'lib' buộc R cài vào thư mục cục bộ
    install.packages(new_pkgs, lib = lib_dir, Ncpus = 4)
  } else {
    message("All packages already installed.")
  }
}

install_if_missing(packages)
