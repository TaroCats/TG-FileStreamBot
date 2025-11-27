/*
 * @Author: ablecats etsy@live.com
 * @LastEditors: ablecats etsy@live.com
 * @LastEditTime: 2025-11-26 17:28:17
 * @Description: 
 */
use tg_filestreambot::{
    config::CONFIG,
    error::AppResult,
    state::AppState,
    utils::{LOGGER, log_startup_info, log_config_info, log_server_startup},
    server,
};
use std::sync::Arc;
use tracing::{info, error, warn};

#[tokio::main]
async fn main() -> AppResult<()> {
    // 自动加载 .env（如果存在）
    let _ = dotenvy::dotenv();

    // 初始化日志系统
    *LOGGER;
    
    // 记录启动信息
    log_startup_info();
    log_config_info(&CONFIG);
    
    // 创建应用状态
    let state = Arc::new(AppState::new());
    
    // 启动 Web 服务器任务
    let server_state = state.clone();
    let server_task = tokio::spawn(async move {
        info!("Starting web server...");
        log_server_startup(&CONFIG.server.bind_address, CONFIG.server.port);
        if let Err(e) = server::start_server(server_state).await {
            error!("Web server error: {}", e);
        }
    });
    
    // 启动后台清理任务
    let cleanup_state = state.clone();
    let cleanup_task = tokio::spawn(async move {
        let mut interval = tokio::time::interval(tokio::time::Duration::from_secs(300)); // 5分钟
        
        loop {
            interval.tick().await;
            
            // 清理过期的流会话
            if let Err(e) = cleanup_state.cleanup_expired_streams().await {
                warn!("Failed to cleanup expired streams: {}", e);
            }
            
            // 清理完成的下载任务
            if let Err(e) = cleanup_state.cleanup_completed_downloads().await {
                warn!("Failed to cleanup completed downloads: {}", e);
            }
        }
    });
    
    // 等待所有任务完成
    tokio::select! {
        _ = server_task => {
            warn!("Web server task completed");
        }
        _ = cleanup_task => {
            warn!("Cleanup task completed");
        }
    }
    
    Ok(())
}