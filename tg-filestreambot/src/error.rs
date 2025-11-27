use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use axum::Json;
use serde_json::json;
use thiserror::Error;

#[derive(Error, Debug)]
pub enum AppError {
    #[error("Telegram API error: {0}")]
    Telegram(String),
    
    #[error("HTTP request error: {0}")]
    Http(#[from] reqwest::Error),
    
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    
    #[error("JSON parsing error: {0}")]
    Json(#[from] serde_json::Error),
    
    #[error("Configuration error: {0}")]
    Config(String),
    
    #[error("File not found")]
    FileNotFound,
    
    #[error("Invalid hash")]
    InvalidHash,
    
    #[error("Cloudreve API error: {0}")]
    Cloudreve(String),
    
    #[error("Download error: {0}")]
    Download(String),
    
    #[error("Request error: {0}")]
    Request(String),
    
    #[error("Stream error: {0}")]
    Stream(String),
    
    #[error("Internal error: {0}")]
    InternalError(String),
    
    #[error("Not found: {0}")]
    NotFound(String),
    
    #[error("Invalid range")]
    InvalidRange,
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let (status, error_message) = match self {
            AppError::NotFound(_) => (StatusCode::NOT_FOUND, self.to_string()),
            AppError::InvalidHash | AppError::InvalidRange => (StatusCode::BAD_REQUEST, self.to_string()),
            AppError::FileNotFound => (StatusCode::NOT_FOUND, self.to_string()),
            _ => (StatusCode::INTERNAL_SERVER_ERROR, self.to_string()),
        };

        let body = json!({
            "error": error_message,
        });

        (status, Json(body)).into_response()
    }
}

pub type AppResult<T> = Result<T, AppError>;