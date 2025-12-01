# Install required R packages for Streamlit app
cat("==========================================\n")
cat("Installing R packages...\n")
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
packages <- c("ggplot2", "dplyr", "gtsummary", "survival", "survminer", "flextable")

cat("Required packages:", paste(packages, collapse = ", "), "\n")
cat("Installing to:", user_lib, "\n\n")

# Function to install a single package with error handling
install_package <- function(pkg) {
  cat(paste0("Installing ", pkg, "...\n"))
  
  tryCatch({
    # Check if already installed
    if (requireNamespace(pkg, quietly = TRUE)) {
      cat(paste0("✓ ", pkg, " already installed\n\n"))
      return(TRUE)
    }
    
    install.packages(
      pkg, 
      lib = user_lib,
      dependencies = TRUE, 
      quiet = FALSE,
      INSTALL_opts = c('--no-lock')
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
  cat("\nTrying alternative installation method...\n\n")
  
  # Try installing failed packages with different method
  for (pkg in failed_packages) {
    cat(paste0("Retrying ", pkg, " with BiocManager...\n"))
    tryCatch({
      if (!requireNamespace("BiocManager", quietly = TRUE)) {
        install.packages("BiocManager", lib = user_lib, quiet = TRUE)
      }
      BiocManager::install(pkg, lib = user_lib, update = FALSE, ask = FALSE)
      
      if (requireNamespace(pkg, quietly = TRUE)) {
        cat(paste0("✓ ", pkg, " installed via BiocManager\n"))
        results[packages == pkg] <- TRUE
      }
    }, error = function(e) {
      cat(paste0("✗ Still failed: ", e$message, "\n"))
    })
  }
  
  # Re-check results
  failed_packages <- packages[!results]
  
  if (length(failed_packages) > 0) {
    cat("\n⚠ Some packages could not be installed:", paste(failed_packages, collapse = ", "), "\n")
    quit(status = 1)
  }
}

cat("\n✓ All packages installed successfully!\n")
cat("Library location:", user_lib, "\n")
quit(status = 0)
