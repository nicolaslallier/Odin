# Confluence Integration Troubleshooting

## Quick Fix: Vault Permission Error

If you're seeing:
```
Error 500: Permission denied reading secret: invalid token
```

### Solution Steps:

1. **Access Vault container:**
   ```bash
   docker exec -it odin-vault sh
   ```

2. **Inside the container, set up the secret:**
   ```bash
   export VAULT_ADDR=http://127.0.0.1:8200
   export VAULT_TOKEN=dev-only-token
   
   # Store Confluence credentials
   vault kv put secret/confluence/credentials \
     base_url="https://your-domain.atlassian.net/wiki" \
     email="your-email@example.com" \
     api_token="your-confluence-api-token"
   
   # Verify
   vault kv get secret/confluence/credentials
   ```

3. **Exit and restart web service:**
   ```bash
   exit
   docker-compose restart web
   ```

### Alternative: From Host Machine

```bash
# Set environment variables
export VAULT_ADDR=http://localhost:8200
export VAULT_TOKEN=dev-only-token

# Store credentials
vault kv put secret/confluence/credentials \
  base_url="https://your-domain.atlassian.net/wiki" \
  email="your-email@example.com" \
  api_token="your-confluence-api-token"

# Verify
vault kv get secret/confluence/credentials
```

## Getting Your Confluence API Token

1. Go to: https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Give it a name (e.g., "Odin Integration")
4. **Copy the token immediately** (you won't see it again!)

## Common Issues

### Issue 1: Wrong Vault Path
❌ **Incorrect:**
```bash
vault kv put confluence/credentials ...
```

✅ **Correct:**
```bash
vault kv put secret/confluence/credentials ...
```

The `secret/` prefix is the KV v2 mount point.

### Issue 2: Vault Token Not Set in Web Service

Check your `docker-compose.yml` has:
```yaml
web:
  environment:
    VAULT_ADDR: http://vault:8200
    VAULT_TOKEN: dev-only-token
```

If missing, add it and restart:
```bash
docker-compose up -d web
```

### Issue 3: Vault Not Running

```bash
# Check if Vault is running
docker-compose ps vault

# If not, start it
docker-compose up -d vault

# Wait a few seconds, then check logs
docker-compose logs vault
```

### Issue 4: KV v2 Engine Not Enabled

In development mode, this should be automatic. But if needed:
```bash
docker exec -it odin-vault vault secrets enable -path=secret kv-v2
```

## Verification Checklist

Run these commands to verify everything is set up correctly:

```bash
# 1. Vault is running
docker-compose ps vault
# Should show: Up

# 2. Can connect to Vault
curl http://localhost:8200/v1/sys/health
# Should return JSON with "initialized": true

# 3. Can read secrets
export VAULT_ADDR=http://localhost:8200
export VAULT_TOKEN=dev-only-token
vault kv get secret/confluence/credentials
# Should show your credentials

# 4. Web service can see Vault
docker-compose logs web | grep -i vault
# Should NOT show connection errors
```

## Test the Integration

Once credentials are stored:

1. Navigate to: http://localhost/confluence
2. Try the "Get Statistics" tab first (simplest operation)
3. Enter a test space key (e.g., "TEST" or your actual space)
4. Click "Get Statistics"

If this works, the integration is properly configured!

## Still Having Issues?

Check the logs:
```bash
# Web service logs
docker-compose logs web --tail=100

# Vault logs
docker-compose logs vault --tail=100

# All services
docker-compose logs --tail=50
```

Look for:
- Connection errors to Vault
- Authentication failures
- Missing environment variables

