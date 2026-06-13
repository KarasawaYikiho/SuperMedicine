#!/usr/bin/env Rscript
# R UMAP dimensionality reduction workspace tool

args <- commandArgs(trailingOnly = TRUE)

tool_kind <- "umap"
input_path <- NULL
output_path <- NULL
check_deps <- FALSE
n_components <- 2L
n_neighbors <- 15L

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
  } else if (args[i] == "--n-components" && i + 1 <= length(args)) {
    n_components <- as.integer(args[i + 1])
    i <- i + 2
  } else if (args[i] == "--n-neighbors" && i + 1 <= length(args)) {
    n_neighbors <- as.integer(args[i + 1])
    i <- i + 2
  } else {
    i <- i + 1
  }
}

required <- c("ggplot2", "readr", "umap")
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
  library(umap)
})

if (!is.null(input_path) && file.exists(input_path)) {
  df <- read_delim(input_path, delim = ifelse(grepl("\\.tsv$", input_path), "\t", ","), show_col_types = FALSE)
} else {
  set.seed(42)
  df <- as.data.frame(matrix(rnorm(100), nrow = 20, ncol = 5))
  colnames(df) <- paste0("feature_", seq_len(ncol(df)))
  rownames(df) <- paste0("sample_", seq_len(nrow(df)))
}

numeric_cols <- vapply(df, is.numeric, logical(1))
mat <- as.matrix(df[, numeric_cols, drop = FALSE])

umap_config <- umap.defaults
umap_config$n_components <- n_components
umap_config$n_neighbors <- n_neighbors

umap_result <- umap(mat, config = umap_config)
embedding <- umap_result$layout
colnames(embedding) <- paste0("UMAP", seq_len(ncol(embedding)))
rownames(embedding) <- rownames(mat)

if (!is.null(output_path)) {
  if (grepl("\\.(png|jpg|svg)$", output_path)) {
    png(output_path, width = 800, height = 600, res = 150)
    plot_df <- as.data.frame(embedding)
    p <- ggplot(plot_df, aes(x = UMAP1, y = UMAP2)) +
      geom_point(size = 3, alpha = 0.7) +
      theme_minimal() +
      ggtitle("UMAP Projection")
    print(p)
    dev.off()
  } else {
    writeLines(jsonlite::toJSON(as.data.frame(embedding), pretty = TRUE), output_path)
  }
  cat(jsonlite::toJSON(list(status = "ok", output = output_path, shape = dim(embedding)), auto_unbox = TRUE), "\n")
} else {
  cat(jsonlite::toJSON(list(
    status = "ok",
    shape = dim(embedding),
    message = "UMAP embedding computed. Use --output to save."
  ), auto_unbox = TRUE), "\n")
}
