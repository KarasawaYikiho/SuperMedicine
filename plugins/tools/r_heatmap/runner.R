#!/usr/bin/env Rscript
# R heatmap visualization workspace tool

args <- commandArgs(trailingOnly = TRUE)

tool_kind <- "heatmap"
input_path <- NULL
output_path <- NULL
check_deps <- FALSE

i <- 1
while (i <= length(args)) {
  if (args[i] == "--tool-kind" && i + 1 <= length(args)) {
    tool_kind <- args[i + 1]
    i <- i + 2
  } else if (args[i] == "--input" && i + 1 <= length(args)) {
    input_path <- args[i + 1]
    i <- i + 2
  } else if (args[i] == "--output" && i + 1 <= length(args)) {
    output_path <- args[i + 1]
    i <- i + 2
  } else if (args[i] == "--check-deps") {
    check_deps <- TRUE
    i <- i + 1
  } else {
    i <- i + 1
  }
}

required <- c("ggplot2", "readr", "pheatmap")
missing <- required[!vapply(required, requireNamespace, quietly = TRUE, FUN.VALUE = logical(1))]

if (check_deps) {
  if (length(missing) > 0) {
    cat(jsonlite::toJSON(list(status = "missing", packages = missing), auto_unbox = TRUE), "\n")
    quit(status = 2)
  }
  cat(jsonlite::toJSON(list(status = "ok", packages = required), auto_unbox = TRUE), "\n")
  quit(status = 0)
}

if (length(missing) > 0) {
  cat("Missing optional R dependencies:", paste(missing, collapse = ", "), "\n")
  cat("Install them in your workspace R library before running this tool.\n")
  quit(status = 2)
}

suppressPackageStartupMessages({
  library(ggplot2)
  library(readr)
  library(pheatmap)
})

if (!is.null(input_path) && file.exists(input_path)) {
  df <- read_delim(input_path, delim = ifelse(grepl("\\.tsv$", input_path), "\t", ","), show_col_types = FALSE)
} else {
  set.seed(42)
  df <- data.frame(
    gene_a = c(1.2, 3.4, 2.1, 4.5, 0.8),
    gene_b = c(2.3, 1.1, 4.2, 0.9, 3.6),
    gene_c = c(3.1, 2.8, 1.5, 3.2, 2.0),
    gene_d = c(0.5, 4.1, 2.9, 1.3, 3.8),
    row.names = paste0("sample_", 1:5)
  )
}

numeric_cols <- vapply(df, is.numeric, logical(1))
mat <- as.matrix(df[, numeric_cols, drop = FALSE])

if (!is.null(output_path)) {
  png(output_path, width = 800, height = 600, res = 150)
  pheatmap(mat, main = "Heatmap", cluster_rows = TRUE, cluster_cols = TRUE)
  dev.off()
  cat(jsonlite::toJSON(list(status = "ok", output = output_path, shape = dim(mat)), auto_unbox = TRUE), "\n")
} else {
  cat(jsonlite::toJSON(list(
    status = "ok",
    shape = dim(mat),
    columns = colnames(mat),
    message = "Heatmap generated. Use --output to save as PNG."
  ), auto_unbox = TRUE), "\n")
}
