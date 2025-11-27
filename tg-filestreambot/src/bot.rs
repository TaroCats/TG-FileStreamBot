use crate::{AppError, AppResult, CONFIG, AppState};
use teloxide::{prelude::*, utils::command::BotCommand};
use std::sync::Arc;
use url::Url;
use chrono::Utc;
use teloxide::types::{Message, InputFile, InlineKeyboardMarkup, InlineKeyboardButton};
use tracing::{info, error, debug};

#[derive(BotCommand, Clone)]
#[command(rename = "lowercase", description = "These commands are supported:")]
pub enum Command {
    #[command(description = "display this text.")]
    Help,
    #[command(description = "show server status.")]
    Status,
    #[command(description = "show download progress.")]
    Progress,
}

pub async fn start_bot(state: AppState) -> AppResult<()> {
    let bot = Bot::new(&CONFIG.telegram.bot_token);
    
    info!("Starting Telegram bot...");
    
    let handler = Update::filter_message()
        .branch(dptree::entry()
            .filter_command::<Command>()
            .endpoint(handle_command))
        .branch(dptree::endpoint(handle_message));
    
    Dispatcher::builder(bot, handler)
        .dependencies(dptree::deps![state])
        .enable_ctrlc_handler()
        .build()
        .dispatch()
        .await;
    
    Ok(())
}

async fn handle_command(
    bot: AutoSend<Bot>,
    msg: Message,
    cmd: Command,
    state: Arc<AppState>,
) -> AppResult<()> {
    match cmd {
        Command::Help => {
            bot.send_message(msg.chat.id, Command::descriptions().to_string())
                .await?;
        }
        Command::Status => {
            let stats = state.get_server_stats();
            let response = format!(
                "🤖 **Server Status**\n\n\
                ⏱️ Uptime: {}\n\
                🌐 Active Streams: {}\n\
                📥 Active Downloads: {}\n\
                📁 Cached Files: {}",
                format_duration(stats.uptime),
                stats.active_streams,
                stats.active_downloads,
                stats.total_files_cached
            );
            bot.send_message(msg.chat.id, response)
                .parse_mode(teloxide::types::ParseMode::MarkdownV2)
                .await?;
        }
        Command::Progress => {
            let downloads = state.get_active_downloads();
            if downloads.is_empty() {
                bot.send_message(msg.chat.id, "No active downloads")
                    .await?;
            } else {
                let mut response = "📥 **Active Downloads**\n\n".to_string();
                for download in downloads {
                    let progress = if download.total_size > 0 {
                        (download.downloaded_size as f64 / download.total_size as f64 * 100.0) as u8
                    } else {
                        0
                    };
                    let status_emoji = match download.status {
                        crate::DownloadStatus::Queued => "⏳",
                        crate::DownloadStatus::Downloading => "⬇️",
                        crate::DownloadStatus::Completed => "✅",
                        crate::DownloadStatus::Failed(_) => "❌",
                        crate::DownloadStatus::Cancelled => "🚫",
                    };
                    response.push_str(&format!(
                        "{} **{}**\n\
                        📊 Progress: {}% ({}/{} bytes)\n\
                        ⚡ Speed: {} bytes/s\n\n",
                        status_emoji,
                        download.url,
                        progress,
                        download.downloaded_size,
                        download.total_size,
                        download.speed
                    ));
                }
                bot.send_message(msg.chat.id, response)
                    .parse_mode(teloxide::types::ParseMode::MarkdownV2)
                    .await?;
            }
        }
    }
    
    Ok(())
}

async fn handle_message(
    bot: AutoSend<Bot>,
    msg: Message,
    state: Arc<AppState>,
) -> AppResult<()> {
    if let Some(text) = msg.text() {
        if text.starts_with("http://") || text.starts_with("https://") {
            handle_url_download(bot, msg, text, state).await?;
        } else {
            bot.send_message(msg.chat.id, "Please send a file or a download URL")
                .await?;
        }
    } else if let Some(document) = msg.document() {
        handle_file_upload(bot, msg, document, state).await?;
    } else {
        bot.send_message(msg.chat.id, "Unsupported message type")
            .await?;
    }
    
    Ok(())
}

async fn handle_url_download(
    bot: AutoSend<Bot>,
    msg: Message,
    url: &str,
    state: Arc<AppState>,
) -> AppResult<()> {
    info!("Processing URL download: {}", url);
    
    // 验证 URL
    match Url::parse(url) {
        Ok(parsed_url) => {
            let task_id = uuid::Uuid::new_v4().to_string();
            
            // 创建下载任务
            match state.create_download_task(task_id.clone(), parsed_url.to_string()).await {
                Ok(_) => {
                    bot.send_message(msg.chat.id, format!("🚀 Download task created: {}", task_id))
                        .await?;
                }
                Err(e) => {
                    error!("Failed to create download task: {}", e);
                    bot.send_message(msg.chat.id, format!("❌ Failed to create download task: {}", e))
                        .await?;
                }
            }
        }
        Err(e) => {
            bot.send_message(msg.chat.id, format!("❌ Invalid URL: {}", e))
                .await?;
        }
    }
    
    Ok(())
}

async fn handle_file_upload(
    bot: AutoSend<Bot>,
    msg: Message,
    document: &teloxide::types::Document,
    state: Arc<AppState>,
) -> AppResult<()> {
    info!("Processing file upload: {:?}", document.file_name);
    
    if let Some(file_name) = &document.file_name {
        let file_size = document.file_size.unwrap_or(0);
        
        // 获取文件信息
        match bot.get_file(&document.file.id).await {
            Ok(file) -> {
                // 创建文件信息记录
                let file_info = crate::FileInfo {
                    file_id: document.file.id.clone(),
                    file_name: file_name.clone(),
                    file_size: file_size as u64,
                    mime_type: document.mime_type.as_ref().map(|m| m.to_string()).unwrap_or_else(|| "application/octet-stream".to_string()),
                    hash: uuid::Uuid::new_v4().to_string(),
                    created_at: Utc::now(),
                    expires_at: Utc::now() + chrono::Duration::hours(24),
                };
                
                // 保存文件信息
                match state.save_file_info(&file_info.hash, file_info.clone()).await {
                    Ok(_) => {
                        let stream_url = format!("{}/stream/{}", CONFIG.server.base_url, file_info.hash);
                        
                        let response = format!(
                            "✅ File uploaded successfully!\n\n\
                            📁 **{}**\n\
                            📊 Size: {} bytes\n\
                            🔗 **Stream URL:**\n\
                            `{}`\n\n\
                            ⚠️ This link expires in 24 hours",
                            file_name,
                            file_size,
                            stream_url
                        );
                        
                        bot.send_message(msg.chat.id, response)
                            .parse_mode(teloxide::types::ParseMode::MarkdownV2)
                            .await?;
                    }
                    Err(e) => {
                        error!("Failed to save file info: {}", e);
                        bot.send_message(msg.chat.id, format!("❌ Failed to save file info: {}", e))
                            .await?;
                    }
                }
            }
            Err(e) => {
                error!("Failed to get file: {}", e);
                bot.send_message(msg.chat.id, format!("❌ Failed to get file: {}", e))
                    .await?;
            }
        }
    } else {
        bot.send_message(msg.chat.id, "❌ File name not available")
            .await?;
    }
    
    Ok(())
}

fn format_duration(duration: std::time::Duration) -> String {
    let secs = duration.as_secs();
    if secs < 60 {
        format!("{}s", secs)
    } else if secs < 3600 {
        format!("{}m {}s", secs / 60, secs % 60)
    } else {
        format!("{}h {}m {}s", secs / 3600, (secs % 3600) / 60, secs % 60)
    }
}