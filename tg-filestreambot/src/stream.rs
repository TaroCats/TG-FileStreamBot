use crate::{AppState, AppError, AppResult};
use dashmap::DashMap;
use std::sync::Arc;
use chrono::{DateTime, Utc};
use std::time::Duration;
use uuid::Uuid;
use tokio::sync::RwLock;
use tracing::{info, warn, error};
use teloxide::Bot;
use teloxide::types::File as TelegramFile;
use bytes::Bytes;
use std::path::Path;
use crate::state::{StreamInfo, DownloadProgress, FileInfo};
use teloxide::net::Download;
use teloxide::prelude::Requester;

#[derive(Debug, Clone)]
pub struct FileStreamManager {
    state: Arc<AppState>,
    active_streams: Arc<DashMap<String, StreamSession>>,
}

#[derive(Debug, Clone)]
pub struct StreamSession {
    pub session_id: String,
    pub file_hash: String,
    pub file_info: FileInfo,
    pub start_time: DateTime<Utc>,
    pub bytes_sent: Arc<RwLock<u64>>,
    pub is_active: Arc<RwLock<bool>>,
}



impl FileStreamManager {
    pub fn new(state: Arc<AppState>) -> Self {
        Self {
            state,
            active_streams: Arc::new(DashMap::new()),
        }
    }
    
    pub async fn create_stream_session(&self, file_hash: &str, file_info: FileInfo) -> AppResult<StreamSession> {
        let session_id = Uuid::new_v4().to_string();
        
        let session = StreamSession {
            session_id: session_id.clone(),
            file_hash: file_hash.to_string(),
            file_info: file_info.clone(),
            start_time: Utc::now(),
            bytes_sent: Arc::new(RwLock::new(0)),
            is_active: Arc::new(RwLock::new(true)),
        };
        
        self.active_streams.insert(session_id.clone(), session.clone());
        
        info!("Created stream session {} for file hash: {}", session_id, file_hash);
        
        Ok(session)
    }
    
    pub async fn end_stream_session(&self, session_id: &str) -> AppResult<()> {
        if let Some((_, session)) = self.active_streams.remove(session_id) {
            *session.is_active.write().await = false;
            
            let duration = Utc::now() - session.start_time;
            let bytes_sent = *session.bytes_sent.read().await;
            
            info!(
                "Ended stream session {} after {} seconds, sent {} bytes",
                session_id,
                duration.num_seconds(),
                bytes_sent
            );
        }
        
        Ok(())
    }
    
    pub async fn get_active_streams(&self) -> Vec<StreamSession> {
        self.active_streams
            .iter()
            .map(|entry| entry.value().clone())
            .collect()
    }
    
    pub async fn stream_file_content(
        &self,
        session: &StreamSession,
        range_start: Option<u64>,
        range_end: Option<u64>,
    ) -> AppResult<Bytes> {
        let bot = Bot::new(&CONFIG.telegram.bot_token);
        
        // 获取文件信息
        let file = bot.get_file(&session.file_info.file_id).await
            .map_err(|e| AppError::Telegram(e.to_string()))?;
        
        // 下载文件内容
        let mut buffer = Vec::new();
        bot.download_file(&file.path, &mut buffer).await
            .map_err(|e| AppError::Telegram(e.to_string()))?;
        
        // 处理范围请求
        let content_length = buffer.len() as u64;
        let start = range_start.unwrap_or(0);
        let end = range_end.unwrap_or(content_length - 1).min(content_length - 1);
        
        if start >= content_length {
            return Err(AppError::Stream("Invalid range".to_string()));
        }
        
        let range_size = (end - start + 1) as usize;
        let range_data = &buffer[start as usize..(start as usize + range_size)];
        
        // 更新发送字节数
        *session.bytes_sent.write().await += range_size as u64;
        
        Ok(Bytes::from(range_data.to_vec()))
    }
    
    pub async fn cleanup_expired_streams(&self) -> AppResult<()> {
        let now = Utc::now();
        let mut expired_sessions = Vec::new();
        
        for entry in self.active_streams.iter() {
            let session = entry.value();
            let duration = now - session.start_time;
            
            // 如果会话超过1小时或者非活跃状态超过5分钟，则清理
            if duration > chrono::TimeDelta::try_hours(1).unwrap() {
                expired_sessions.push(session.session_id.clone());
            } else if !*session.is_active.read().await {
                let last_activity = now - session.start_time;
                if last_activity > chrono::Duration::minutes(5) {
                    expired_sessions.push(session.session_id.clone());
                }
            }
        }
        
        for session_id in expired_sessions {
            self.end_stream_session(&session_id).await?;
        }
        
        Ok(())
    }
}

// 下载进度管理器
pub struct DownloadManager {
    active_downloads: Arc<DashMap<String, DownloadProgress>>,
}

impl DownloadManager {
    pub fn new() -> Self {
        Self {
            active_downloads: Arc::new(DashMap::new()),
        }
    }
    
    pub async fn create_download_task(&self, task_id: &str, url: &str) -> AppResult<()> {
        let progress = DownloadProgress {
            task_id: task_id.to_string(),
            url: url.to_string(),
            status: crate::state::DownloadStatus::Pending,
            progress: 0.0,
            total_size: 0,
            downloaded_size: 0,
            speed: 0,
            eta: None,
            started_at: Utc::now(),
            updated_at: Utc::now(),
        };
        
        self.active_downloads.insert(task_id.to_string(), progress);
        
        info!("Created download task: {} for URL: {}", task_id, url);
        
        Ok(())
    }
    
    pub async fn update_download_progress(
        &self,
        task_id: &str,
        status: DownloadStatus,
        _progress: f64,
        total_size: u64,
        downloaded_size: u64,
        speed: u64,
    ) -> AppResult<()> {
        if let Some(mut entry) = self.active_downloads.get_mut(task_id) {
            let progress = entry.value_mut();
            progress.status = status;
            progress.progress = progress.progress.min(100.0);
            progress.total_size = total_size;
            progress.downloaded_size = downloaded_size;
            progress.speed = speed;
            progress.updated_at = Utc::now();
            
            // 计算预计完成时间
            if speed > 0 && downloaded_size < total_size {
                let remaining = total_size - downloaded_size;
                progress.eta = Some(remaining / speed);
            } else {
                progress.eta = None;
            }
        }
        
        Ok(())
    }
    
    pub async fn get_download_progress(&self, task_id: &str) -> Option<DownloadProgress> {
        self.active_downloads.get(task_id).map(|entry| entry.value().clone())
    }
    
    pub async fn get_all_downloads(&self) -> Vec<DownloadProgress> {
        self.active_downloads
            .iter()
            .map(|entry| entry.value().clone())
            .collect()
    }
    
    pub async fn remove_download_task(&self, task_id: &str) -> AppResult<()> {
        self.active_downloads.remove(task_id);
        info!("Removed download task: {}", task_id);
        Ok(())
    }
    
    pub async fn cleanup_completed_downloads(&self) -> AppResult<()> {
        let now = Utc::now();
        let mut completed_tasks = Vec::new();
        
        for entry in self.active_downloads.iter() {
            let progress = entry.value();
            
            // 如果任务已完成或失败超过1小时，则清理
            match &progress.status {
                crate::state::DownloadStatus::Completed | crate::state::DownloadStatus::Failed(_) => {
                    let duration = now - progress.updated_at;
                    if duration.num_seconds() > 3600 {
                        completed_tasks.push(progress.task_id.clone());
                    }
                }
                _ => {}
            }
        }
        
        for task_id in completed_tasks {
            self.remove_download_task(&task_id).await?;
        }
        
        Ok(())
    }
}

// 文件缓存管理器
pub struct FileCache {
    cache: Arc<DashMap<String, FileInfo>>,
    max_cache_size: usize,
}

impl FileCache {
    pub fn new(max_cache_size: usize) -> Self {
        Self {
            cache: Arc::new(DashMap::new()),
            max_cache_size,
        }
    }
    
    pub async fn add_file(&self, file_hash: &str, file_info: FileInfo) -> AppResult<()> {
        // 如果缓存已满，清理一些旧文件
        if self.cache.len() >= self.max_cache_size {
            self.cleanup_old_files().await?;
        }
        
        self.cache.insert(file_hash.to_string(), file_info.clone());
        
        info!("Added file to cache: {} ({})", file_info.file_name, file_hash);
        
        Ok(())
    }
    
    pub async fn get_file(&self, file_hash: &str) -> Option<FileInfo> {
        self.cache.get(file_hash).map(|entry| entry.value().clone())
    }
    
    pub async fn remove_file(&self, file_hash: &str) -> AppResult<()> {
        self.cache.remove(file_hash);
        info!("Removed file from cache: {}", file_hash);
        Ok(())
    }
    
    pub async fn get_cache_size(&self) -> usize {
        self.cache.len()
    }
    
    pub async fn cleanup_old_files(&self) -> AppResult<()> {
        // 简单的清理策略：移除一半的文件
        let keys: Vec<String> = self.cache.iter().map(|entry| entry.key().clone()).take(self.max_cache_size / 2).collect();
        let cleanup_count = keys.len();
        
        for key in keys {
            self.cache.remove(&key);
        }
        
        info!("Cleaned up {} old files from cache", cleanup_count);
        
        Ok(())
    }
}