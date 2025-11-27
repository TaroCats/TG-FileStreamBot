use crate::{AppError, AppResult};
use dashmap::DashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use chrono::{DateTime, Utc};
use std::time::Duration;
use uuid::Uuid;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone)]
pub struct FileInfo {
    pub file_id: String,
    pub file_name: String,
    pub file_size: u64,
    pub mime_type: String,
    pub hash: String,
    pub created_at: DateTime<Utc>,
    pub expires_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DownloadProgress {
    pub task_id: String,
    pub url: String,
    pub progress: f64,
    pub speed: u64,
    pub eta: Option<u64>,
    pub status: DownloadStatus,
    pub total_size: u64,
    pub downloaded_size: u64,
    pub started_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum DownloadStatus {
    Pending,
    Downloading,
    Completed,
    Failed,
    Cancelled,
}

#[derive(Debug, Clone)]
pub struct StreamInfo {
    pub session_id: String,
    pub file_hash: String,
    pub file_name: String,
    pub file_size: u64,
    pub start_time: DateTime<Utc>,
    pub client_ip: String,
}

#[derive(Debug, Clone)]
pub struct ServerStats {
    pub uptime: std::time::Duration,
    pub active_streams: u64,
    pub total_streams: u64,
    pub active_downloads: u64,
    pub total_downloads: u64,
    pub cached_files: usize,
    pub total_requests: u64,
    pub bytes_served: u64,
    pub start_time: DateTime<Utc>,
}

#[derive(Debug, Clone)]
pub struct AppState {
    pub file_cache: Arc<DashMap<String, FileInfo>>,
    pub download_progress: Arc<DashMap<String, DownloadProgress>>,
    pub active_streams: Arc<DashMap<String, StreamInfo>>,
    pub server_stats: Arc<RwLock<ServerStats>>,
    pub start_time: DateTime<Utc>,
}

impl AppState {
    pub fn new() -> Self {
        let server_stats = ServerStats {
            uptime: Duration::from_secs(0),
            active_streams: 0,
            total_streams: 0,
            active_downloads: 0,
            total_downloads: 0,
            cached_files: 0,
            total_requests: 0,
            bytes_served: 0,
            start_time: Utc::now(),
        };
        
        Self {
            file_cache: Arc::new(DashMap::new()),
            download_progress: Arc::new(DashMap::new()),
            active_streams: Arc::new(DashMap::new()),
            server_stats: Arc::new(RwLock::new(server_stats)),
            start_time: Utc::now(),
        }
    }
    
    // 文件缓存管理
    pub fn add_file_to_cache(&self, file_info: FileInfo) {
        self.file_cache.insert(file_info.hash.clone(), file_info);
    }
    
    pub fn get_file_from_cache(&self, hash: &str) -> Option<FileInfo> {
        self.file_cache.get(hash).map(|entry| entry.clone())
    }
    
    pub fn remove_file_from_cache(&self, hash: &str) -> Option<FileInfo> {
        self.file_cache.remove(hash).map(|(_, file)| file)
    }
    
    pub fn cleanup_expired_files(&self) -> AppResult<usize> {
        let now = Utc::now();
        let mut removed_count = 0;
        
        self.file_cache.retain(|_, file_info| {
            if file_info.expires_at < now {
                removed_count += 1;
                false
            } else {
                true
            }
        });
        
        Ok(removed_count)
    }
    
    // 下载进度管理
    pub fn create_download_progress(&self, url: String) -> String {
        let task_id = Uuid::new_v4().to_string();
        let progress = DownloadProgress {
            task_id: task_id.clone(),
            url,
            progress: 0.0,
            speed: 0,
            eta: None,
            status: DownloadStatus::Pending,
            total_size: 0,
            downloaded_size: 0,
            started_at: Utc::now(),
            updated_at: Utc::now(),
        };
        
        self.download_progress.insert(task_id.clone(), progress);
        task_id
    }
    
    pub fn update_download_progress(&self, task_id: &str, progress: f64, speed: u64, eta: Option<u64>) -> AppResult<()> {
        if let Some(mut entry) = self.download_progress.get_mut(task_id) {
            entry.progress = progress;
            entry.speed = speed;
            entry.eta = eta;
            entry.updated_at = Utc::now();
            
            if progress >= 100.0 {
                entry.status = DownloadStatus::Completed;
            }
            
            Ok(())
        } else {
            Err(AppError::NotFound(format!("Download task {} not found", task_id)))
        }
    }
    
    pub fn get_download_progress(&self, task_id: &str) -> Option<DownloadProgress> {
        self.download_progress.get(task_id).map(|entry| entry.clone())
    }
    
    pub fn remove_download_progress(&self, task_id: &str) -> Option<DownloadProgress> {
        self.download_progress.remove(task_id).map(|(_, progress)| progress)
    }
    
    pub fn get_all_download_progress(&self) -> Vec<DownloadProgress> {
        self.download_progress.iter().map(|entry| entry.clone()).collect()
    }
    
    // 流会话管理
    pub fn create_stream_session(&self, session_info: StreamInfo) {
        self.active_streams.insert(session_info.session_id.clone(), session_info);
    }
    
    pub fn end_stream_session(&self, session_id: &str) -> Option<StreamInfo> {
        self.active_streams.remove(session_id).map(|(_, info)| info)
    }
    
    pub fn get_active_streams(&self) -> Vec<StreamInfo> {
        self.active_streams.iter().map(|entry| entry.clone()).collect()
    }
    
    pub async fn cleanup_expired_streams(&self) -> AppResult<usize> {
        let now = Utc::now();
        let mut removed_count = 0;
        
        // 假设流会话在30分钟后过期
        let expired_time = now - Duration::from_secs(1800);
        
        self.active_streams.retain(|_, stream_info| {
            if stream_info.start_time < expired_time {
                removed_count += 1;
                false
            } else {
                true
            }
        });
        
        Ok(removed_count)
    }
    
    // 统计信息更新
    pub async fn update_server_stats<F>(&self, updater: F) -> AppResult<()>
    where
        F: FnOnce(&mut ServerStats),
    {
        let mut stats = self.server_stats.write().await;
        updater(&mut *stats);
        Ok(())
    }
    
    pub async fn get_server_stats(&self) -> ServerStats {
        let mut stats = self.server_stats.write().await;
        let elapsed = Utc::now() - stats.start_time;
        stats.uptime = std::time::Duration::from_secs(elapsed.num_seconds() as u64);
        stats.cached_files = self.file_cache.len();
        stats.active_downloads = self.download_progress.len() as u64;
        stats.active_streams = self.active_streams.len() as u64;
        stats.clone()
    }
    
    // 清理完成的下载任务
    pub async fn cleanup_completed_downloads(&self) -> AppResult<usize> {
        let mut removed_count = 0;
        
        self.download_progress.retain(|_, progress| {
            match progress.status {
                DownloadStatus::Completed | DownloadStatus::Failed | DownloadStatus::Cancelled => {
                    removed_count += 1;
                    false
                }
                _ => true,
            }
        });
        
        Ok(removed_count)
    }
}