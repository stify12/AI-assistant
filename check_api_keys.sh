#!/bin/bash
docker exec ai-mysql mysql -u aiuser -paipass123 aiuser 2>/dev/null <<'EOF'
SHOW TABLES;
EOF
