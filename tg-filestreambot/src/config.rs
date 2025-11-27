use serde::{Deserialize, Serialize};
use std::env;
use once_cell::sync::Lazy;
use anyhow::Result;

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct Config {
    pub telegram: TelegramConfig,
    pub server: ServerConfig,
    pub cloudreve: CloudreveConfig,
    pub logging: LoggingConfig,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct TelegramConfig {
    pub api_id: i32,
    pub api_hash: String,
    pub bot_token: String,
    pub bin_channel: i64,
    pub multi_tokens: Vec<String>,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct ServerConfig {
    pub port: u16,
    pub bind_address: String,
    pub hash_length: usize,
    pub fqdn: Option<String>,
    pub has_ssl: bool,
    pub no_port: bool,
    pub workers: usize,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct CloudreveConfig {
    pub enabled: bool,
    pub api_url: String,
    pub username: String,
    pub password: String,
    pub download_path: String,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct LoggingConfig {
    pub level: String,
    pub format: String,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            telegram: TelegramConfig {
                api_id: 0,
                api_hash: String::new(),
                bot_token: String::new(),
                bin_channel: 0,
                multi_tokens: Vec::new(),
            },
            server: ServerConfig {
                port: 8080,
                bind_address: "0.0.0.0".to_string(),
                hash_length: 6,
                fqdn: None,
                has_ssl: false,
                no_port: false,
                workers: 3,
            },
            cloudreve: CloudreveConfig {
                enabled: false,
                api_url: String::new(),
                username: String::new(),
                password: String::new(),
                download_path: "/".to_string(),
            },
            logging: LoggingConfig {
                level: "info".to_string(),
                format: "json".to_string(),
            },
        }
    }
}

pub static CONFIG: Lazy<Config> = Lazy::new(|| {
    load_config().expect("Failed to load configuration")
});

pub fn load_config() -> Result<Config> {
    // 移除dotenv依赖
    
    let mut config = Config::default();
    
    // Telegram 配置
    config.telegram.api_id = env::var("API_ID")?.parse()?;
    config.telegram.api_hash = env::var("API_HASH")?;
    config.telegram.bot_token = env::var("BOT_TOKEN")?;
    config.telegram.bin_channel = env::var("BIN_CHANNEL")?.parse()?;
    
    // 多客户端令牌
    for i in 1..=10 {
        if let Ok(token) = env::var(format!("MULTI_TOKEN{}", i)) {
            config.telegram.multi_tokens.push(token);
        }
    }
    
    // 服务器配置
    if let Ok(port) = env::var("PORT") {
        config.server.port = port.parse()?;
    }
    if let Ok(bind) = env::var("WEB_SERVER_BIND_ADDRESS") {
        config.server.bind_address = bind;
    }
    if let Ok(hash_len) = env::var("HASH_LENGTH") {
        config.server.hash_length = hash_len.parse()?;
    }
    if let Ok(fqdn) = env::var("FQDN") {
        config.server.fqdn = Some(fqdn);
    }
    if let Ok(ssl) = env::var("HAS_SSL") {
        config.server.has_ssl = ssl.to_lowercase() == "true";
    }
    if let Ok(no_port) = env::var("NO_PORT") {
        config.server.no_port = no_port.to_lowercase() == "true";
    }
    if let Ok(workers) = env::var("WORKERS") {
        config.server.workers = workers.parse()?;
    }
    
    // Cloudreve 配置
    if let Ok(enabled) = env::var("USE_CLOUDEREVE") {
        config.cloudreve.enabled = enabled.to_lowercase() == "true";
    }
    if let Ok(url) = env::var("CLOUDEREVE_API_URL") {
        config.cloudreve.api_url = url;
    }
    if let Ok(user) = env::var("CLOUDEREVE_USERNAME") {
        config.cloudreve.username = user;
    } else if let Ok(email) = env::var("CLOUDEREVE_EMAIL") {
        config.cloudreve.username = email;
    }
    if let Ok(pass) = env::var("CLOUDEREVE_PASSWORD") {
        config.cloudreve.password = pass;
    }
    if let Ok(path) = env::var("CLOUDEREVE_DOWNLOAD_PATH") {
        config.cloudreve.download_path = path;
    }
    
    // 日志配置
    if let Ok(level) = env::var("LOG_LEVEL") {
        config.logging.level = level;
    }
    
    Ok(config)
}