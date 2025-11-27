use once_cell::sync::Lazy;

use std::time::Duration;
use tracing::{info, warn, error, debug};
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

pub static LOGGER: Lazy<()> = Lazy::new(|| {
    init_logger();
});

pub fn init_logger() {
    // 初始化日志系统
    tracing_subscriber::registry()
        .with(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "info".into()),
        )
        .with(tracing_subscriber::fmt::layer())
        .init();
    
    info!("🚀 TG FileStreamBot Logger initialized");
}

pub fn log_startup_info() {
    info!("╔══════════════════════════════════════════════════════════════════════════════════════════════╗");
    info!("║                                    🚀 TG FileStreamBot                                      ║");
    info!("║                                                                                             ║");
    info!("║  High-performance Telegram file streaming service powered by Rust                           ║");
    info!("║  Features:                                                                                  ║");
    info!("║    • Async/await with Tokio runtime                                                        ║");
    info!("║    • Zero-copy file streaming                                                              ║");
    info!("║    • Concurrent request handling                                                           ║");
    info!("║    • Cloudreve integration                                                                 ║");
    info!("║    • Real-time progress tracking                                                           ║");
    info!("║    • Memory-efficient caching                                                              ║");
    info!("║                                                                                             ║");
    info!("╚══════════════════════════════════════════════════════════════════════════════════════════════╝");
}

pub fn log_config_info(config: &crate::config::Config) {
    info!("📋 Configuration loaded:");
    info!("  • Telegram Bot: {} clients configured", config.telegram.bot_token.len());
    info!("  • Web Server: {}:{}", config.server.bind_address, config.server.port);
    info!("  • Workers: {}", config.server.workers);
    info!("  • Cloudreve: {}", if config.cloudreve.enabled { "Enabled" } else { "Disabled" });
    
    if config.cloudreve.enabled {
        info!("  • Cloudreve API: {}", config.cloudreve.api_url);
        info!("  • Download Path: {}", config.cloudreve.download_path);
    }
    
    info!("  • Log Level: {}", config.logging.level);
}

pub fn log_server_startup(bind_addr: &str, port: u16) {
    info!("🌐 Web server started on http://{}:{}", bind_addr, port);
    info!("📊 Health check available at: http://{}:{}/api/status", bind_addr, port);
    info!("📈 Statistics available at: http://{}:{}/api/stats", bind_addr, port);
}

pub fn log_telegram_startup() {
    info!("🤖 Telegram bot started and listening for messages");
}

pub fn log_stream_session_created(session_id: &str, file_name: &str, file_size: u64) {
    info!("📡 Stream session created: {} for file: {} ({} bytes)", session_id, file_name, file_size);
}

pub fn log_stream_session_ended(session_id: &str, duration: Duration, bytes_sent: u64) {
    let speed = if duration.as_secs() > 0 {
        bytes_sent as f64 / duration.as_secs() as f64
    } else {
        0.0
    };
    
    info!("🏁 Stream session ended: {} after {:.2}s, {} bytes sent, {:.2} bytes/s", 
          session_id, duration.as_secs_f64(), bytes_sent, speed);
}

pub fn log_download_task_created(task_id: &str, url: &str) {
    info!("⬇️  Download task created: {} for URL: {}", task_id, url);
}

pub fn log_download_progress(task_id: &str, progress: f64, speed: u64, eta: Option<u64>) {
    let eta_str = match eta {
        Some(seconds) if seconds > 0 => format!(", ETA: {}s", seconds),
        _ => String::new(),
    };
    
    debug!("⬇️  Download progress: {} - {:.1}% at {} bytes/s{}", 
           task_id, progress, speed, eta_str);
}

pub fn log_download_completed(task_id: &str, total_size: u64, duration: Duration) {
    let speed = if duration.as_secs() > 0 {
        total_size as f64 / duration.as_secs() as f64
    } else {
        0.0
    };
    
    info!("✅ Download completed: {} - {} bytes in {:.2}s, {:.2} bytes/s", 
          task_id, total_size, duration.as_secs_f64(), speed);
}

pub fn log_download_failed(task_id: &str, error: &str) {
    error!("❌ Download failed: {} - {}", task_id, error);
}

pub fn log_cache_hit(file_hash: &str) {
    debug!("💾 Cache hit for file: {}", file_hash);
}

pub fn log_cache_miss(file_hash: &str) {
    debug!("💾 Cache miss for file: {}", file_hash);
}

pub fn log_cache_added(file_hash: &str, file_name: &str) {
    info!("💾 File added to cache: {} ({})", file_name, file_hash);
}

pub fn log_cache_cleanup(count: usize) {
    info!("🧹 Cache cleanup: removed {} old files", count);
}

pub fn log_error(error: &str, context: &str) {
    error!("❌ Error in {}: {}", context, error);
}

pub fn log_warning(warning: &str, context: &str) {
    warn!("⚠️  Warning in {}: {}", context, warning);
}

pub fn log_info(message: &str, context: &str) {
    info!("ℹ️  Info in {}: {}", context, message);
}

pub fn log_debug(message: &str, context: &str) {
    debug!("🔍 Debug in {}: {}", context, message);
}

// 性能监控相关的日志函数
pub fn log_performance_metric(metric: &str, value: f64, unit: &str) {
    info!("📊 Performance metric - {}: {:.2} {}", metric, value, unit);
}

pub fn log_memory_usage(used_mb: f64, total_mb: f64) {
    let percentage = (used_mb / total_mb) * 100.0;
    info!("🧠 Memory usage: {:.1}MB / {:.1}MB ({:.1}%)", used_mb, total_mb, percentage);
}

pub fn log_request_processed(method: &str, path: &str, duration: Duration, status_code: u16) {
    info!("🌐 Request processed: {} {} - {} in {:.2}ms", 
          method, path, status_code, duration.as_secs_f64() * 1000.0);
}