# Install required R packages for Streamlit app (minimal version)
cat("==========================================\n")
cat("Checking and installing R packages...\n")
cat("==========================================\n\n")

# Set CRAN mirror
options(repos = c(CRAN = "https://cloud.r-project.org/"))

# Create user library directory if it doesn't exist
user_lib <- Sys.getenv("R_LIBS_USER")
if (user_lib == "") {
  user_lib <- file.path(Sys.getenv("HOME"), "R", "library")
}
if (!dir.exists(user_lib)) {
  dir.create(user_lib, recursive = TRUE)
  cat("Created user library directory:", user_lib, "\n")
}

# Add user library to library paths
.libPaths(c(user_lib, .libPaths()))
cat("Library paths:", .libPaths(), "\n\n")

# List of required packages
# Note: ggplot2, dplyr, survival should be pre-installed via packages.txt
packages <- c("ggplot2", "dplyr", "gtsummary", "survival", "survminer", "flextable")
cat("Required packages:", paste(packages, collapse = ", "), "\n\n")

# Check which packages are missing
missing_packages <- c()
for (pkg in packages) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    missing_packages <- c(missing_packages, pkg)
    cat("✗", pkg, "not found\n")
  } else {
    cat("✓", pkg, "already installed\n")
  }
}

if (length(missing_packages) == 0) {
  cat("\n✓ All packages are already installed!\n")
  quit(status = 0)
}

cat("\nInstalling missing packages:", paste(missing_packages, collapse = ", "), "\n")
cat("Installing to:", user_lib, "\n\n")

# Function to install a single package
install_package <- function(pkg) {
  cat(paste0("Installing ", pkg, "...\n"))
  
  tryCatch({
    install.packages(
      pkg, 
      lib = user_lib,
      dependencies = TRUE, 
      quiet = TRUE,
      INSTALL_opts = c('--no-lock', '--no-test-load')
    )
    
    if (requireNamespace(pkg, quietly = TRUE)) {
      cat(paste0("✓ ", pkg, " installed\n\n"))
      return(TRUE)
    } else {
      cat(paste0("✗ ", pkg, " failed\n\n"))
      return(FALSE)
    }
  }, error = function(e) {
    cat(paste0("✗ Error: ", e$message, "\n\n"))
    return(FALSE)
  })
}

# Install only missing packages
results <- sapply(missing_packages, install_package)

# Summary
cat("\n==========================================\n")
cat("Installation Summary\n")
cat("==========================================\n")
if (all(results)) {
  cat("✓ All packages installed successfully!\n")
  quit(status = 0)
} else {
  failed <- missing_packages[!results]
  cat("⚠ Some packages failed:", paste(failed, collapse = ", "), "\n")
  cat("The app may still work with pre-installed packages.\n")
  quit(status = 0)  # Don't fail completely
}
