#!/usr/bin/env Rscript

arg_value <- function(args, flag, default = NULL) {
  idx <- match(flag, args)
  if (!is.na(idx) && length(args) >= idx + 1) return(args[[idx + 1]])
  default
}

sample_data <- function() {
  data.frame(
    x1 = c(1, 2, 3, 4, 5),
    x2 = c(2, 3, 5, 8, 13),
    group = c("A", "A", "B", "B", "B"),
    target = c(0, 0, 1, 1, 1),
    stringsAsFactors = FALSE
  )
}

read_rows <- function(path) {
  if (is.null(path) || path == "") return(sample_data())
  if (!file.exists(path)) stop(paste("input file not found:", path))
  read.table(path, header = TRUE, sep = "", stringsAsFactors = FALSE, check.names = FALSE)
}

numeric_columns <- function(df, requested) {
  if (!is.null(requested) && requested != "") {
    names <- trimws(strsplit(requested, ",")[[1]])
  } else {
    names <- colnames(df)
  }
  out <- list()
  for (name in names) {
    if (!name %in% colnames(df)) next
    values <- suppressWarnings(as.numeric(df[[name]]))
    values <- values[is.finite(values)]
    if (length(values) > 0) out[[name]] <- values
  }
  if (length(out) == 0) stop("no numeric columns found for analysis")
  out
}

emit <- function(value, output) {
  text <- paste(capture.output(print(value)), collapse = "\n")
  if (!is.null(output) && output != "") writeLines(text, output) else cat(text, "\n", sep = "")
}

descriptive <- function(cols) {
  lapply(cols, function(x) list(count = length(x), mean = mean(x), sd = sd(x), min = min(x), median = median(x), max = max(x)))
}

missing_summary <- function(df) {
  lapply(df, function(x) list(missing = sum(is.na(x) | trimws(as.character(x)) == ""), missing_rate = mean(is.na(x) | trimws(as.character(x)) == "")))
}

scale_summary <- function(cols) {
  lapply(cols, function(x) list(z_score = as.numeric(scale(x)), min_max = if (diff(range(x)) == 0) rep(0, length(x)) else (x - min(x)) / diff(range(x))))
}

correlation_summary <- function(cols) {
  data <- as.data.frame(cols)
  list(pearson = cor(data, method = "pearson"), spearman = cor(data, method = "spearman"))
}

linear_regression <- function(cols) {
  data <- as.data.frame(cols)
  if (ncol(data) < 2) stop("linear-regression requires at least two numeric columns")
  fit <- lm(data[[2]] ~ data[[1]])
  list(coefficients = coef(fit), r_squared = summary(fit)$r.squared)
}

logistic_regression <- function(cols) {
  data <- as.data.frame(cols)
  if (ncol(data) < 2) stop("logistic-regression requires predictor and binary target columns")
  target <- ifelse(data[[2]] > 0, 1, 0)
  fit <- glm(target ~ data[[1]], family = binomial())
  list(coefficients = coef(fit))
}

pca_summary <- function(cols) {
  data <- as.data.frame(cols)
  if (ncol(data) < 2) stop("pca requires at least two numeric columns")
  fit <- prcomp(data, scale. = TRUE)
  list(explained_variance = fit$sdev ^ 2, rotation = fit$rotation)
}

kmeans_summary <- function(cols) {
  data <- as.data.frame(cols)
  k <- min(2, nrow(data))
  fit <- kmeans(data, centers = k, nstart = 5)
  list(centers = fit$centers, cluster = fit$cluster)
}

hierarchical_summary <- function(cols) {
  data <- as.data.frame(cols)
  fit <- hclust(dist(t(data)), method = "complete")
  list(method = fit$method, order = fit$order, labels = fit$labels)
}

optional_wrapper <- function(kind) {
  packages <- if (kind == "random-forest") c("randomForest") else c("xgboost", "lightgbm")
  missing <- packages[!vapply(packages, requireNamespace, quietly = TRUE, FUN.VALUE = logical(1))]
  list(algorithm = kind, optional = TRUE, status = if (length(missing) > 0) "missing_optional_dependencies" else "available", missing_dependencies = missing)
}

time_series_summary <- function(cols) {
  x <- cols[[1]]
  list(n = length(x), mean = mean(x), first_difference_mean = if (length(x) > 1) mean(diff(x)) else 0, lag1_autocorrelation = if (length(x) > 2) cor(x[-length(x)], x[-1]) else 0)
}

hypothesis <- function(kind, df, cols) {
  if (kind == "t-test") {
    x <- cols[[1]]; mid <- floor(length(x) / 2)
    return(t.test(x[1:mid], x[(mid + 1):length(x)]))
  }
  if (kind == "chi-square") {
    factors <- Filter(function(name) length(unique(df[[name]])) > 1, colnames(df))
    if (length(factors) < 2) stop("chi-square requires two categorical columns")
    return(chisq.test(table(df[[factors[1]]], df[[factors[2]]])))
  }
  group_col <- setdiff(colnames(df), names(cols))[1]
  if (is.na(group_col)) stop("anova requires a categorical group column")
  value_col <- names(cols)[1]
  summary(aov(df[[value_col]] ~ as.factor(df[[group_col]])))
}

run_action <- function(kind, df, cols) {
  switch(kind,
    "descriptive" = descriptive(cols),
    "missing" = missing_summary(df),
    "scale" = scale_summary(cols),
    "correlation" = correlation_summary(cols),
    "linear-regression" = linear_regression(cols),
    "logistic-regression" = logistic_regression(cols),
    "pca" = pca_summary(cols),
    "kmeans" = kmeans_summary(cols),
    "hierarchical-clustering" = hierarchical_summary(cols),
    "random-forest" = optional_wrapper("random-forest"),
    "gradient-boosting" = optional_wrapper("gradient-boosting"),
    "time-series" = time_series_summary(cols),
    "t-test" = hypothesis("t-test", df, cols),
    "chi-square" = hypothesis("chi-square", df, cols),
    "anova" = hypothesis("anova", df, cols),
    stop(paste("unsupported tool-kind:", kind))
  )
}

args <- commandArgs(trailingOnly = TRUE)
input <- arg_value(args, "--input")
output <- arg_value(args, "--output")
kind <- arg_value(args, "--tool-kind", "all-light")
columns <- arg_value(args, "--columns")

if ("--check-deps" %in% args) {
  cat("Baseline R data-analysis actions use base/recommended R packages; heavy ML wrappers are optional.\n")
  quit(status = 0)
}

tryCatch({
  df <- read_rows(input)
  cols <- numeric_columns(df, columns)
  if (kind == "all-light") {
    kinds <- c("descriptive", "missing", "scale", "correlation", "linear-regression", "logistic-regression", "pca", "kmeans", "hierarchical-clustering", "time-series", "t-test", "chi-square", "anova")
    result <- lapply(kinds, function(k) tryCatch(run_action(k, df, cols), error = function(e) list(error = conditionMessage(e))))
    names(result) <- kinds
  } else {
    result <- run_action(kind, df, cols)
  }
  emit(list(status = "ok", tool_kind = kind, result = result), output)
}, error = function(e) {
  cat(paste("ERROR:", conditionMessage(e), "\n"), file = stderr())
  quit(status = 2)
})
