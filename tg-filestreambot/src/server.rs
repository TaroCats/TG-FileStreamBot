use axum::{
    extract::{Path, Query, State},
    http::{StatusCode, header},
    response::{Response, IntoResponse},
    routing::get,
    Router,
    Json,
    body::Body,
};
use std::sync::Arc;
use chrono::Utc;
use uuid::Uuid;
use crate::{AppState, AppError, AppResult, CONFIG, FileInfo, StreamInfo};
use tracing::info;
use axum::response::Html;

#[axum::debug_handler]
async fn api_status(State(state): State<Arc<AppState>>) -> AppResult<Json<serde_json::Value>> {
    let stats = state.get_server_stats().await;
    
    Ok(Json(serde_json::json!({
        "status": "ok",
        "uptime": stats.uptime.as_secs(),
        "active_streams": stats.active_streams,
        "active_downloads": stats.active_downloads,
        "cached_files": stats.cached_files,
        "total_requests": stats.total_requests,
    })))
}

#[derive(serde::Deserialize)]
struct StreamParams {
    start: Option<u64>,
    end: Option<u64>,
}

pub async fn start_server(state: Arc<AppState>) -> AppResult<()> {
    
    let app = Router::new()
        .route("/", get(root_handler))
        .route("/:hash", get(stream_handler))
        .route("/api/status", get(api_status))
        .with_state(state);

    let addr = format!("{}:{}", CONFIG.server.bind_address, CONFIG.server.port);
    info!("Starting server on {}", addr);
    
    let listener = tokio::net::TcpListener::bind(&addr).await?;
    axum::serve(listener, app).await?;
    
    Ok(())
}

async fn root_handler() -> impl IntoResponse {
    Html(format!(r#"<!DOCTYPE html>
<html>
<head>
    <title>TG FileStream Bot</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .container {{ max-width: 800px; margin: 0 auto; }}
        .status {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-top: 20px; }}
        .stat-card {{ background: white; padding: 15px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .stat-value {{ font-size: 24px; font-weight: bold; color: #007bff; }}
        .stat-label {{ color: #666; margin-top: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 TG FileStream Bot</h1>
        <p>高性能 Telegram 文件直链服务</p>
        
        <div class="status">
            <h3>服务状态</h3>
            <p>✅ 服务运行正常</p>
            <p>📊 实时统计: <a href="/api/stats">API 统计</a></p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">在线</div>
                <div class="stat-label">服务状态</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">高速</div>
                <div class="stat-label">传输模式</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">Rust</div>
                <div class="stat-label">技术栈</div>
            </div>
        </div>
    </div>
</body>
</html>"#))
}

async fn stream_handler(
    Path(hash): Path<String>,
    State(state): State<Arc<AppState>>,
    Query(params): Query<StreamParams>,
) -> AppResult<Response> {
    info!("Stream request for hash: {}", hash);
    
    // 获取文件信息
    let file_info = state.get_file_from_cache(&hash).ok_or_else(|| AppError::NotFound(format!("File with hash {} not found", hash)))?;
    
    // 创建流会话
    let session_info = StreamInfo {
        session_id: Uuid::new_v4().to_string(),
        file_hash: hash.clone(),
        file_name: file_info.file_name.clone(),
        file_size: file_info.file_size,
        start_time: Utc::now(),
        client_ip: "127.0.0.1".to_string(), // 简化处理，实际应从请求头获取
    };
    state.create_stream_session(session_info);
    
    // 处理范围请求
    let start = params.start.unwrap_or(0);
    let end = params.end.unwrap_or(file_info.file_size - 1);
    
    // 构建响应
    build_stream_response(file_info, start, end).await
}

async fn build_stream_response(
    file_info: FileInfo,
    start: u64,
    end: u64,
) -> AppResult<Response> {
    let content_length = end - start + 1;
    let content_range = format!("bytes {}-{}/{}", start, end, file_info.file_size);
    
    let response_builder = Response::builder()
        .status(if start == 0 && end == file_info.file_size - 1 { StatusCode::OK } else { StatusCode::PARTIAL_CONTENT })
        .header(header::CONTENT_TYPE, &file_info.mime_type)
        .header(header::ACCEPT_RANGES, "bytes")
        .header(header::CACHE_CONTROL, "public, max-age=3600")
        .header(header::CONTENT_RANGE, content_range)
        .header(header::CONTENT_LENGTH, content_length.to_string())
        .header(header::CONTENT_DISPOSITION, format!("inline; filename=\"{}\"", file_info.file_name));
    
    Ok(response_builder.body(Body::empty()).map_err(|e| AppError::InternalError(e.to_string()))?)
}