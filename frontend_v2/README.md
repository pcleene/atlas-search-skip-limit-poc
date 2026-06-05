# Automotive Parts Catalog Search - Frontend

A clean, responsive frontend UI matching PartsDistributor's design language.

## 🚀 Quick Start

### Option 1: Python HTTP Server
```bash
cd frontend_v2
python -m http.server 8081
```

Then open: http://localhost:8081

### Option 2: Node.js HTTP Server
```bash
cd frontend_v2
npx http-server -p 8081
```

Then open: http://localhost:8081

### Option 3: Direct File
Simply open `index.html` in your browser.

**Note**: Make sure the backend is running on http://localhost:8001

## 📁 Project Structure

```
frontend/
├── index.html           # Main HTML page
├── css/
│   └── styles.css      # All styles (modern CSS)
├── js/
│   ├── api.js          # API client for backend
│   └── app.js          # Main application logic
└── README.md
```

## ✨ Features

### Search
- **Live Search** - Debounced search as you type (300ms delay)
- **Autocomplete** - Real-time suggestions after 2+ characters
- **Clear Button** - Quick reset of search query

### Filters
- **Dynamic Facets** - Automatically populated from search results
- **Multiple Filters** - Select multiple values per facet
- **Apply/Clear** - Apply or reset all filters at once

### Results
- **Part Cards** - Clean card layout matching PartsDistributor design
- **Sort Options** - Sort by price, update date, or part number
- **Rows Per Page** - Choose 20, 50, or 100 results
- **Instant Updates** - Results update as you interact

### Pagination
- **Page-Based** - Simple offset pagination (skip/limit)
- **Next/Previous** - Navigate forward and backward
- **Page Info** - Shows current range and total count
- **Page Numbers** - Track which page you're on

## 🎨 Design

The UI closely matches PartsDistributor's actual interface:

### Color Scheme
- Primary: `#5b9bd5` (Blue)
- Secondary: `#2e75b5` (Dark Blue)
- Accent: `#ffc107` (Amber)
- Background: `#f8f9fa` (Light Gray)

### Components
1. **Header** - Logo, navigation, cart, user avatar
2. **Search Bar** - Large, prominent search input
3. **Controls Bar** - Sort, rows per page, filters
4. **Filter Panel** - Collapsible faceted filters
5. **Part Cards** - Detailed part information
6. **Pagination** - Simple prev/next navigation

## 🔧 Configuration

### API URL
Edit `js/api.js`:

```javascript
const API_BASE_URL = 'http://localhost:8001';  // V2 uses port 8001
```

For production, change to your deployed backend URL.

### Default Settings
Edit in `js/app.js`:

```javascript
this.currentSearchParams = {
    searchText: '',
    sortBy: 'price',      // Default sort field
    sortOrder: 'asc',     // Default sort order
    limit: 20,            // Default page size
    filters: { ... }
};
```

## 🧪 Testing

### Test Autocomplete
1. Type "ms" in search bar
2. Wait for suggestions to appear
3. Click a suggestion or press Enter

### Test Search
1. Search for "MS24694"
2. Results should load in <300ms
3. Facets should populate on the side

### Test Filters
1. Click "Filter" button
2. Select "New" condition
3. Select "KULMS" location
4. Click "Apply Filters"
5. Results should filter instantly

### Test Pagination
1. Scroll to bottom
2. Click "Next" button
3. Page 2 should load instantly
4. Click "Previous"
5. Should return to page 1

## 📱 Responsive Design

The UI is fully responsive:

- **Desktop** (>768px): Full layout with sidebar filters
- **Tablet** (768px): Stacked layout, collapsible filters
- **Mobile** (<768px): Single column, simplified navigation

## 🎯 Key Files

### index.html
- Semantic HTML structure
- Accessibility features (ARIA labels)
- Clean, minimal markup

### css/styles.css
- Modern CSS (Flexbox, Grid, Variables)
- Responsive breakpoints
- Smooth animations and transitions
- No external dependencies

### js/api.js
- API client class
- Fetch-based requests
- Query string building
- Request cancellation support

### js/app.js
- Main application state
- Event handling
- DOM manipulation
- Search debouncing
- Pagination logic

## 🚀 Performance

Optimizations:
- **Debounced Search** - Reduces API calls
- **Request Cancellation** - Cancels outdated requests
- **Lazy Loading** - Images and data loaded as needed
- **CSS Animations** - Smooth, GPU-accelerated
- **No Framework** - Minimal bundle size

Expected performance:
- Page load: <500ms
- Search response: <300ms (including network)
- Filter application: Instant
- Pagination: Instant

## 🎨 Customization

### Change Colors
Edit CSS variables in `css/styles.css`:

```css
:root {
    --primary-color: #5b9bd5;
    --secondary-color: #2e75b5;
    --accent-color: #ffc107;
    ...
}
```

### Change Layout
Modify grid/flexbox in `css/styles.css`:

```css
.part-details {
    display: grid;
    grid-template-columns: repeat(3, 1fr); /* Change column count */
    gap: 15px;
}
```

### Add New Filters
1. Add facet in backend
2. Add container in HTML:
   ```html
   <div id="newFilterFilters"></div>
   ```
3. Update facet mapping in `app.js`

## 🐛 Troubleshooting

### No Results Showing
- Open browser console (F12)
- Check for errors
- Verify backend is running
- Check CORS settings

### Autocomplete Not Working
- Must type at least 2 characters
- Wait 300ms for debounce
- Check network tab for API calls

### Filters Not Applying
- Check facets are returned from API
- Verify checkbox IDs match facet values
- Check browser console for errors

### Styling Issues
- Clear browser cache
- Check CSS file is loaded
- Verify no CSS conflicts

## 📚 Learn More

- [Fetch API](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API)
- [CSS Grid](https://css-tricks.com/snippets/css/complete-guide-grid/)
- [CSS Flexbox](https://css-tricks.com/snippets/css/a-guide-to-flexbox/)
- [Modern JavaScript](https://javascript.info/)

---

**Built with vanilla JavaScript - no frameworks, no build step, no dependencies!**
