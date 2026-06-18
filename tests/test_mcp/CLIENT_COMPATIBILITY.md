# MCP Client Compatibility Matrix

This document outlines the compatibility of the WMS MCP Server with various MCP clients.

## Supported Clients

| Client | Version | Transport | Status | Notes |
|--------|---------|----------|--------|-------|
| Claude Desktop | Latest | stdio | ✅ Supported | Full feature support |
| Claude Web | Latest | SSE | ✅ Supported | Full feature support |
| MCP CLI | Latest | stdio | ✅ Supported | Full feature support |
| Custom Python Clients | 1.0+ | stdio/SSE | ✅ Supported | Requires MCP SDK |

## Transport Support

| Transport | Status | Notes |
|----------|--------|-------|
| stdio | ✅ Supported | Default transport for CLI clients |
| SSE | ✅ Supported | Recommended for web clients |

## Feature Compatibility

| Feature | Claude Desktop | Claude Web | MCP CLI | Custom Clients |
|---------|---------------|------------|---------|---------------|
| Tool Discovery | ✅ | ✅ | ✅ | ✅ |
| Tool Execution | ✅ | ✅ | ✅ | ✅ |
| Error Handling | ✅ | ✅ | ✅ | ✅ |
| Authentication | ✅ | ✅ | ✅ | ✅ |
| Rate Limiting | ✅ | ✅ | ✅ | ✅ |

## Known Limitations

- SSE transport may have latency in high-latency networks
- Custom clients must implement proper error handling
- Rate limiting is enforced per API key

## Testing

All clients are tested for compatibility with each release.
