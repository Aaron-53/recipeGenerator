# Qdrant Data Transfer Guide

This guide explains how to transfer your Qdrant vector database and recipe embeddings to another system.

## 📍 **Data Location**

Your Qdrant data is now stored persistently in:

```
d:\miniProj\qdrant_storage\
```

This directory contains all your vector collections, including the recipe embeddings you've generated.

## 🚀 **Quick Transfer Commands**

### 1. Create a Backup

```bash
# Create timestamped backup
python qdrant_setup.py backup

# Create backup with custom name
python qdrant_setup.py backup my_recipes_backup
```

### 2. Check Storage Info

```bash
python qdrant_setup.py storage
```

### 3. Transfer to Another System

**Option A: Copy the entire storage directory**

```bash
# Compress the data
tar -czf qdrant_data.tar.gz qdrant_storage/

# Or on Windows with 7-zip
7z a qdrant_data.7z qdrant_storage\
```

**Option B: Use the backup system**

```bash
# Create backup first
python qdrant_setup.py backup transfer_backup

# Compress the backup
tar -czf qdrant_backup.tar.gz transfer_backup/
```

## 🎯 **Setting Up on New System**

### Method 1: Direct Storage Copy

1. Install Docker on the new system
2. Copy the `qdrant_storage` folder to your new project directory
3. Run `python qdrant_setup.py start`
4. Your data will be automatically available

### Method 2: Using Backup/Restore

1. Transfer the backup archive to the new system
2. Extract it: `tar -xzf qdrant_backup.tar.gz`
3. Run: `python qdrant_setup.py restore transfer_backup`
4. Start Qdrant: `python qdrant_setup.py start`

## 📊 **What Gets Transferred**

- **Vector Collections**: All your recipe embeddings
- **Collection Configuration**: Vector dimensions, distance metrics
- **Metadata**: Recipe data, titles, indices
- **Search Indices**: Optimized search structures

## 🔍 **Verification After Transfer**

1. **Check status:**

   ```bash
   python qdrant_setup.py status
   ```

2. **Test search:**

   ```bash
   python qdrant_query.py
   ```

3. **Verify data in dashboard:**
   ```
   http://localhost:6333/dashboard
   ```

## 💾 **Storage Structure**

```
qdrant_storage/
├── collections/
│   └── recipe_embeddings/
│       ├── 0/
│       │   ├── segments/
│       │   └── wal/
│       └── aliases/
├── meta/
└── snapshots/
```

## ⚠️ **Important Notes**

- **Stop Qdrant** before copying data: `python qdrant_setup.py stop`
- **Match versions**: Use same Qdrant Docker image version on both systems
- **Verify permissions**: Ensure Docker can read the storage directory
- **Check disk space**: Recipe embeddings can be several GB

## 🆘 **Troubleshooting Transfer Issues**

### Permission Problems

```bash
# Fix permissions on Linux/Mac
sudo chown -R $(whoami) qdrant_storage/

# On Windows, run as Administrator
```

### Version Mismatch

```bash
# Check Qdrant version
docker run --rm qdrant/qdrant:latest --version

# Use specific version if needed
docker run -d --name qdrant_local \
  -p 6333:6333 -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage \
  qdrant/qdrant:v1.7.0
```

### Partial Transfer

```bash
# Restore from backup if transfer was incomplete
python qdrant_setup.py stop
python qdrant_setup.py restore <backup_path>
python qdrant_setup.py start
```

## 📈 **Size Estimates**

- **~3KB per recipe** (768-dim vector + metadata)
- **100K recipes ≈ 300MB**
- **1M recipes ≈ 3GB**

Your actual transfer size depends on the number of recipes processed.

---

**🎉 Happy transferring!** Your recipe embeddings are now portable and can run anywhere Docker is available.
