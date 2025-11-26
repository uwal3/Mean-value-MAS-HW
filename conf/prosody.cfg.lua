

admins = { }

data_path = "/var/lib/prosody"

modules_enabled = {
    "roster"; 
    "saslauth";
    "tls";      
    "disco";    
    "register"; 
}

allow_registration = true 

c2s_require_encryption = false 

authentication = "internal_plain"

log = {
    info = "*console";
    error = "*console";
}

VirtualHost "localhost"