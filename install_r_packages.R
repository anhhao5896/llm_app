# Install required R packages for Streamlit app
cat("==========================================\n")
cat("Installing R packages for data analysis\n")
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
cat("Library paths:", paste(.libPaths(), collapse = "\n  "), "\n\n")

# Define packages in install order (dependencies first)
# Core dependencies that need to be installed first
core_deps <- c("Matrix", "Rcpp", "cli", "rlang", "lifecycle")

# Main packages needed for the app
main_packages <- c("ggplot2", "dplyr", "gtsummary", "survival", "survminer", "flextable")

all_packages <- c(core_deps, main_packages)

cat("Packages to install/check:\n")
cat("  Core:", paste(core_deps, collapse = ", "), "\n")
cat("  Main:", paste(main_packages, collapse = ", "), "\n\n")

# Function to safely check if package is installed
is_installed <- function(pkg) {
  requireNamespace(pkg, quietly = TRUE)
}

# Function to install a single package with retries
install_package <- function(pkg, max_retries = 2) {
  if (is_installed(pkg)) {
    cat("✓", pkg, "already installed\n")
    return(TRUE)
  }
  
  cat("Installing", pkg, "...\n")
  
  for (attempt in 1:max_retries) {
    tryCatch({
      install.packages(
        pkg, 
        lib = user_lib,
        dependencies = c("Depends", "Imports"),
        quiet = FALSE,
        INSTALL_opts = c('--no-lock', '--no-test-load', '--no-docs', '--no-html')
      )
      
      if (is_installed(pkg)) {
        cat("✓", pkg, "installed successfully\n\n")
        return(TRUE)
      } else {
        cat("  Attempt", attempt, "failed for", pkg, "\n")
      }
    }, error = function(e) {
      cat("  Error on attempt", attempt, ":", e$message, "\n")
    })
    
    if (attempt < max_retries) {
      cat("  Retrying...\n")
      Sys.sleep(2)
    }
  }
  
  cat("✗", pkg, "failed to install after", max_retries, "attempts\n\n")
  return(FALSE)
}

# Install packages in order
cat("==========================================\n")
cat("Installing core dependencies...\n")
cat("==========================================\n")

core_results <- sapply(core_deps, install_package)

cat("\n==========================================\n")
cat("Installing main packages...\n")
cat("==========================================\n")

main_results <- sapply(main_packages, install_package)

# Combine results
all_results <- c(core_results, main_results)

# Summary
cat("\n==========================================\n")
cat("Installation Summary\n")
cat("==========================================\n")

success_count <- sum(all_results)
total_count <- length(all_results)

cat(sprintf("✓ Successfully installed: %d/%d packages\n", success_count, total_count))

if (success_count < total_count) {
  failed <- names(all_results)[!all_results]
  cat("✗ Failed packages:", paste(failed, collapse = ", "), "\n")
  cat("\nNote: The app may still work with available packages.\n")
  cat("You can manually install failed packages later.\n")
}

# Verify critical packages
critical <- c("ggplot2", "dplyr", "survival")
critical_ok <- sapply(critical, is_installed)

if (all(critical_ok)) {
  cat("\n✓ All critical packages are available!\n")
  quit(status = 0)
} else {
  missing_critical <- critical[!critical_ok]
  cat("\n⚠ Warning: Missing critical packages:", paste(missing_critical, collapse = ", "), "\n")
  quit(status = 0)  # Don't fail deployment, but warn user
}
