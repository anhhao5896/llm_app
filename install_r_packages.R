# Install required R packages for Streamlit app
cat("==========================================\n")
cat("Installing R packages...\n")
cat("==========================================\n\n")

# Set CRAN mirror
options(repos = c(CRAN = "https://cloud.r-project.org/"))

# List of required packages
packages <- c("ggplot2", "dplyr", "gtsummary", "survival", "survminer", "flextable")

cat("Required packages:", paste(packages, collapse = ", "), "\n\n")

# Function to install a single package with error handling
install_package <- function(pkg) {
  cat(paste0("Installing ", pkg, "...\n"))
  
  tryCatch({
    install.packages(
      pkg, 
      dependencies = TRUE, 
      quiet = FALSE,
      verbose = TRUE
    )
    
    # Verify installation
    if (requireNamespace(pkg, quietly = TRUE)) {
      cat(paste0("✓ ", pkg, " installed successfully\n\n"))
      return(TRUE)
    } else {
      cat(paste0("✗ ", pkg, " installation failed (verification failed)\n\n"))
      return(FALSE)
    }
  }, error = function(e) {
    cat(paste0("✗ Error installing ", pkg, ": ", e$message, "\n\n"))
    return(FALSE)
  })
}

# Install packages one by one
results <- sapply(packages, install_package)

# Summary
cat("\n==========================================\n")
cat("Installation Summary\n")
cat("==========================================\n")

installed_packages <- packages[results]
failed_packages <- packages[!results]

if (length(installed_packages) > 0) {
  cat("Successfully installed:", paste(installed_packages, collapse = ", "), "\n")
}

if (length(failed_packages) > 0) {
  cat("Failed to install:", paste(failed_packages, collapse = ", "), "\n")
  cat("\nYou can try installing these manually in R:\n")
  cat("install.packages(c(", paste(paste0("'", failed_packages, "'"), collapse = ", "), "))\n")
  quit(status = 1)
} else {
  cat("\n✓ All packages installed successfully!\n")
  quit(status = 0)
}
