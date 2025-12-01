# Minimal check - do NOT install anything new
cat("Checking pre-installed R packages...\n\n")

packages <- c("ggplot2", "dplyr", "survival")

for (pkg in packages) {
  if (requireNamespace(pkg, quietly = TRUE)) {
    cat("✓", pkg, "available\n")
  } else {
    cat("✗", pkg, "not found\n")
  }
}

cat("\n✓ Check complete - no additional installation\n")
cat("Note: Using base R packages only (fast deployment)\n")

quit(status = 0)
