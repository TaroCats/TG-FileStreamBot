use crate::{AppResult, AppError, CONFIG};
use reqwest::{Client, Response};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::RwLock;
use chrono::{DateTime, Utc};
use tracing::{info, warn, error};

#[derive(Debug, Clone)]
pub struct CloudreveClient {
    client: reqwest::Client,
    base_url: String,
    auth_token: Arc<RwLock<Option<String>>>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct LoginRequest {
    pub username: String,
    pub password: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct LoginResponse {
    pub code: i32,
    pub data: Option<LoginData>,
    pub msg: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct LoginData {
    pub token: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct CreateDownloadRequest {
    pub url: String,
    pub path: String,
    pub tool: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct DownloadTask {
    pub id: String,
    pub status: String,
    pub error: Option<String>,
    pub progress: i32,
    pub total: i64,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct FileListResponse {
    pub code: i32,
    pub data: Option<FileListData>,
    pub msg: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct FileListData {
    pub objects: Vec<FileObject>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct FileObject {
    pub id: String,
    pub name: String,
    pub path: String,
    pub size: i64,
    pub type_: String,
    pub created_at: DateTime<Utc>,
}

impl CloudreveClient {
    pub fn new() -> Self {
        let client = reqwest::Client::builder()
            .timeout(std::time::Duration::from_secs(30))
            .build()
            .unwrap();
        
        Self {
            client,
            base_url: CONFIG.cloudreve.api_url.clone(),
            auth_token: Arc::new(RwLock::new(None)),
        }
    }
    
    pub async fn login(&self) -> AppResult<()> {
        let login_data = LoginRequest {
            username: CONFIG.cloudreve.username.clone(),
            password: CONFIG.cloudreve.password.clone(),
        };
        
        let response = self.client
            .post(&format!("{}/api/v3/user/session", self.base_url))
            .json(&login_data)
            .send()
            .await?;
        
        let login_response: LoginResponse = response.json().await?;
        
        if login_response.code == 0 {
            if let Some(data) = login_response.data {
                let mut token = self.auth_token.write().await;
                *token = Some(data.token);
                info!("Successfully logged into Cloudreve");
                return Ok(());
            }
        }
        
        Err(AppError::Cloudreve(format!(
            "Login failed: {}",
            login_response.msg
        )))
    }
    
    pub async fn ensure_authenticated(&self) -> AppResult<String> {
        // 检查是否有有效的 token
        {
            let token = self.auth_token.read().await;
            if let Some(ref t) = *token {
                return Ok(t.clone());
            }
        }
        
        // 如果没有 token，重新登录
        self.login().await?;
        
        let token = self.auth_token.read().await;
        token.clone().ok_or_else(|| AppError::Cloudreve("Failed to get authentication token".to_string()))
    }
    
    pub async fn create_download_task(&self, url: &str, path: &str) -> AppResult<String> {
        let token = self.ensure_authenticated().await?;
        
        let download_request = CreateDownloadRequest {
            url: url.to_string(),
            path: path.to_string(),
            tool: Some("aria2".to_string()),
        };
        
        let response = self.client
            .post(&format!("{}/api/v3/aria2/url", self.base_url))
            .header("Authorization", format!("Bearer {}", token))
            .json(&download_request)
            .send()
            .await?;
        
        let result: serde_json::Value = response.json().await?;
        
        if result["code"] == 0 {
            if let Some(task_id) = result["data"]["gid"].as_str() {
                info!("Created download task: {} for URL: {}", task_id, url);
                return Ok(task_id.to_string());
            }
        }
        
        Err(AppError::Cloudreve(format!(
            "Failed to create download task: {}",
            result["msg"].as_str().unwrap_or("Unknown error")
        )))
    }
    
    pub async fn get_download_status(&self, task_id: &str) -> AppResult<DownloadTask> {
        let token = self.ensure_authenticated().await?;
        
        let response = self.client
            .get(&format!("{}/api/v3/aria2/status/{}", self.base_url, task_id))
            .header("Authorization", format!("Bearer {}", token))
            .send()
            .await?;
        
        let result: serde_json::Value = response.json().await?;
        
        if result["code"] == 0 {
            if let Some(data) = result["data"].as_object() {
                return Ok(DownloadTask {
                    id: task_id.to_string(),
                    status: data["status"].as_str().unwrap_or("unknown").to_string(),
                    error: data["error"].as_str().map(|s| s.to_string()),
                    progress: data["progress"].as_i64().unwrap_or(0) as i32,
                    total: data["total"].as_i64().unwrap_or(0),
                    created_at: Utc::now(),
                });
            }
        }
        
        Err(AppError::Cloudreve(format!(
            "Failed to get download status for task: {}",
            task_id
        )))
    }
    
    pub async fn list_files(&self, path: &str) -> AppResult<Vec<FileObject>> {
        let token = self.ensure_authenticated().await?;
        
        let response = self.client
            .get(&format!("{}/api/v3/directory/{}", self.base_url, path))
            .header("Authorization", format!("Bearer {}", token))
            .send()
            .await?;
        
        let result: FileListResponse = response.json().await?;
        
        if result.code == 0 {
            if let Some(data) = result.data {
                return Ok(data.objects);
            }
        }
        
        Err(AppError::Cloudreve(format!(
            "Failed to list files in path: {}",
            path
        )))
    }
    
    pub async fn search_downloads_by_url(&self, _url: &str) -> AppResult<Vec<DownloadTask>> {
        // 简化实现：列出下载目录中的文件
        let _files = self.list_files(&CONFIG.cloudreve.download_path).await?;
        
        // 这里应该实现实际的搜索逻辑
        // 暂时返回空列表
        Ok(vec![])
    }
}

pub async fn create_cloudreve_client() -> CloudreveClient {
    let client = CloudreveClient::new();
    
    // 尝试登录
    if let Err(e) = client.login().await {
        error!("Failed to login to Cloudreve: {}", e);
    }
    
    client
}