# VTU Auto Diary Filler

A user-friendly console application for automatically uploading internship diary entries to the VTU portal.

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.11+-green)
![License](https://img.shields.io/badge/license-MIT-purple)

> ⚠️ **Disclaimer: Educational Purposes Only**  
> This project is a completely independent, unofficial tool built strictly for educational purposes and learning Python automation. It is **not** endorsed by, affiliated with, or supported by VTU in any capacity. Users assume all responsibility and liability for how they utilize this application. Please ensure you comply with all university guidelines regarding portal usage.

## ✨ Features

- 🎯 **Easy to Use** - Intuitive menu system with rich console interface
- 🔐 **Secure** - Encrypted password storage
- 📅 **Smart Date Management** - Automatic date assignment and holiday detection
- 📊 **View & Download** - Access all your existing entries
- ⚙️ **Setup Wizard** - Guided configuration for first-time users
- 🚀 **Single Executable** - No installation required

## 🚀 Quick Start

### For Windows Users (Recommended)

1. **Download the executable**
   - Get `AutoDiary.exe` from the [releases](https://github.com/AsimAftab/AutoDiary/releases) page
   - Place it anywhere on your computer

2. **Run the application**
   - Double-click `AutoDiary.exe`
   - Follow the setup wizard

3. **Start uploading diaries!**
   - Select "Upload Diaries" from the main menu
   - Choose your upload options
   - Watch the progress

### For Advanced Users

If you prefer to run from source code:

```bash
# Clone the repository
git clone https://github.com/AsimAftab/AutoDiary.git
cd AutoDiary

# Complete installation instantly
uv sync

# Run the application using uv run
uv run python -m autodiary
# Or using the registered command:
uv run autodiary
```

## 📖 How to Use

### First Run

When you first run the application, you'll be guided through a setup wizard that asks for:

1. **VTU Credentials**
   - Your VTU portal email
   - Your VTU portal password

2. **Internship Details**
   - Internship ID
   - Start date (YYYY-MM-DD format)
   - End date (YYYY-MM-DD or "today")
   - Internship title and company (optional)

3. **Holiday Configuration**
   - Select weekend days (e.g., Sunday)
   - Add specific holiday dates if needed

### Main Menu

After setup, you'll see the main menu:

```
┌─────────────────────────────────┐
│  VTU Auto Diary Filler          │
│  Internship at Company          │
└─────────────────────────────────┘

What would you like to do?

  📤 Upload Diaries
  📥 View/Download Entries
  ⚙️  Configuration
  🔐 Login & Authentication
  ❓ Help & Documentation
  0. 🚪 Exit
```

### Upload Diaries

1. **Upload with Auto-Dates** (Recommended)
   - Automatically assigns dates to your entries
   - Skips holidays and weekends
   - Skips existing entries on server

2. **Upload Specific Date Range**
   - Upload entries for a specific period
   - Useful for bulk uploads

3. **Dry Run**
   - Validate entries without uploading
   - Great for testing

4. **Upload from File**
   - Upload entries from a specific JSON file

5. **Interactive Upload**
   - Review each entry before uploading
   - Choose which entries to upload

### View Entries

1. **View All Existing Entries**
   - See all entries uploaded to the portal
   - Paginated display for easy navigation

2. **View by Date Range**
   - Filter entries by date range
   - Find specific entries quickly

3. **View Entry Statistics**
   - Total entries and hours
   - Average hours and mood
   - Mood distribution
   - Top skills used

4. **Download All Entries**
   - Download all entries as JSON
   - Backup your data

5. **Export to CSV**
   - Export entries for spreadsheet analysis

## 📝 Diary Entry Format

Your diary entries should be in JSON format:

```json
[
  {
    "description": "Worked on data analysis using Python and SQL",
    "hours": 8,
    "links": "https://github.com/project",
    "blockers": "",
    "learnings": "Improved SQL query optimization techniques",
    "mood_slider": 5,
    "skill_ids": ["44", "16", "20"]
  }
]
```

**Required Fields:**
- `description` - What you worked on
- `hours` - Hours worked (1-24)
- `learnings` - Key learnings from the day
- `mood_slider` - Mood rating (1-5)
- `skill_ids` - List of skill IDs (see "Help > View Available Skills" in the app)

**💡 Finding Skill IDs:**
- Open the app and go to "Help & Documentation"
- Select "View Available Skills"
- Browse 100+ available skills with their IDs
- Common skills: Python (3), JavaScript (1), Data modeling (44), SQL (20)

**Optional Fields:**
- `date` - Entry date (YYYY-MM-DD format)
- `links` - Related links
- `blockers` - Any blockers encountered
- `internship_id` - Override default internship ID

## 🔧 Configuration

You can access configuration options from the main menu:

### Edit Credentials
- Update your VTU email and password
- Test login after updating

### Edit Internship Settings
- Update internship details
- Change start/end dates

### Edit Holiday Settings
- Modify weekend days
- Add/remove specific holidays

### Advanced Settings
- Request timeout
- Request delays
- Maximum retries
- Auto-skip existing entries

### Test Connection
- Verify your credentials work
- Check API connectivity

### Reset to Defaults
- Clear all configuration
- Run setup wizard again

## 🔐 Security

- **Encrypted Storage**: Your password is encrypted using Fernet symmetric encryption
- **Local Configuration**: All data is stored locally on your computer
- **No Telemetry**: No data is sent to external servers except the VTU API
- **Open Source**: Code is available for audit

## ❓ Troubleshooting

### Login Issues

**Problem**: "Login failed"
- **Solution**: Check your email and password in Configuration
- **Solution**: Verify VTU portal is accessible
- **Solution**: Try "Test Connection" in Authentication menu

### Upload Issues

**Problem**: "Upload failed for some entries"
- **Solution**: Check your internet connection
- **Solution**: Verify entries have valid dates
- **Solution**: Try "Dry Run" first to validate entries

**Problem**: "Holiday detected"
- **Solution**: Entries on holidays are automatically skipped
- **Solution**: Update holiday settings in Configuration

### Configuration Issues

**Problem**: "Configuration file corrupted"
- **Solution**: Go to Configuration → Reset to Defaults
- **Solution**: Run setup wizard again

**Problem**: "Wrong internship dates"
- **Solution**: Go to Configuration → Edit Internship Settings
- **Solution**: Update your dates

### Performance Issues

**Problem**: "Application is slow"
- **Solution**: Check your internet speed and connection stability
- **Solution**: Try increasing timeout in advanced settings if requests are timing out

**Problem**: "Application freezes"
- **Solution**: Close and restart the application

## 📚 Additional Resources

- **User Guide**: Available in-app via Help menu
- **Troubleshooting Guide**: Detailed troubleshooting in `docs/TROUBLESHOOTING.txt`
- **Quick Start**: Quick reference in `docs/QUICKSTART.txt`
- **GitHub Repository**: [https://github.com/AsimAftab/AutoDiary](https://github.com/AsimAftab/AutoDiary)
- **Issue Tracker**: Report bugs and request features

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
Check out our complete [Development Guide](docs/DEVELOPMENT.md) for onboarding instructions!

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- VTU for providing the internship portal
- The open-source community for amazing tools
- Contributors and users of this application

## 📞 Support

If you need help:
- Check the in-app Help menu
- Read the troubleshooting guide
- Visit our GitHub repository
- Open an issue on GitHub

---

Made with ❤️ for VTU students
