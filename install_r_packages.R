# Install required R packages
packages <- c("ggplot2", "dplyr", "gtsummary", "survival", "survminer", "flextable")

# Set CRAN mirror
options(repos = c(CRAN = "https://cloud.r-project.org/"))

# Install packages
install.packages(packages, dependencies = TRUE, quiet = FALSE)

# Verify installation
installed <- sapply(packages, function(pkg) {
  requireNamespace(pkg, quietly = TRUE)
})

if (all(installed)) {
  cat("All packages installed successfully!\n")
  cat("Installed packages:", paste(packages, collapse = ", "), "\n")
} else {
  cat("Failed to install:", paste(packages[!installed], collapse = ", "), "\n")
  quit(status = 1)
}
