# Inventory Management Frontend

A React-based frontend application for the Inventory Management System. This application connects to the FastAPI backend and provides a complete user interface for managing inventory items.

## Features

### Authentication

- **User Registration**: Create new accounts with username and password
- **User Login**: Secure login with JWT token authentication
- **Google OAuth**: Sign in with Google account
- **Protected Routes**: Automatic redirection to login for unauthenticated users
- **Password Validation**: Strong password requirements
  - Minimum 8 characters
  - At least one uppercase letter
  - At least one lowercase letter
  - At least one digit

### Inventory Management

- **Create Items**: Add new inventory items with name, quantity, unit, category, and notes
- **View Items**: Display all items in a responsive grid layout
- **Edit Items**: Update existing inventory items
- **Delete Items**: Remove items from inventory
- **Filter by Category**: View items filtered by category
- **Statistics Dashboard**: See total items and category breakdown

## Backend API Routes Utilized

### Authentication Routes (`/auth`)

- `POST /auth/register` - Register new user
- `POST /auth/login` - Login and get JWT token
- `POST /auth/logout` - Logout user
- `GET /auth/me` - Get current user information
- `GET /auth/verify-token` - Verify JWT token validity
- `GET /auth/google/login` - Initiate Google OAuth flow
- `GET /auth/google/callback` - Handle Google OAuth callback
- `POST /auth/google/verify` - Verify Google ID token

### Inventory Routes (`/inventory`)

- `POST /inventory/items` - Create new inventory item
- `GET /inventory/items` - Get all inventory items (with optional category filter)
- `GET /inventory/items/{item_id}` - Get specific inventory item
- `PUT /inventory/items/{item_id}` - Update inventory item
- `DELETE /inventory/items/{item_id}` - Delete inventory item
- `GET /inventory/stats` - Get inventory statistics

### Health Check Routes

- `GET /` - Root endpoint
- `GET /health` - Health check endpoint

## Project Structure

```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── components/
│   │   ├── InventoryForm.js
│   │   ├── InventoryForm.css
│   │   ├── InventoryList.js
│   │   ├── InventoryList.css
│   │   ├── InventoryStats.js
│   │   ├── InventoryStats.css
│   │   └── PrivateRoute.js
│   ├── context/
│   │   └── AuthContext.js
│   ├── pages/
│   │   ├── AuthCallback.js
│   │   ├── AuthPages.css
│   │   ├── Dashboard.js
│   │   ├── Dashboard.css
│   │   ├── Login.js
│   │   └── Register.js
│   ├── services/
│   │   └── api.js
│   ├── App.js
│   ├── App.css
│   ├── index.js
│   └── index.css
└── package.json
```

## Installation

1. Navigate to the frontend directory:

```bash
cd frontend
```

2. Install dependencies:

```bash
npm install
```

## Configuration

Create a `.env` file in the frontend directory (optional):

```env
REACT_APP_API_URL=http://localhost:8000
```

If not set, the application will default to `http://localhost:8000`.

## Running the Application

1. Make sure the backend server is running on `http://localhost:8000`

2. Start the development server:

```bash
npm start
```

3. Open your browser and navigate to `http://localhost:3000`

## Building for Production

To create a production build:

```bash
npm run build
```

The build files will be in the `build/` directory.

## Usage

### First Time Setup

1. Navigate to the application in your browser
2. Click "Register here" to create a new account
3. Fill in username and password (or use Google OAuth)
4. You'll be automatically logged in and redirected to the dashboard

### Managing Inventory

1. Click "Add Item" to create a new inventory item
2. Fill in the required fields:
   - Item Name (required)
   - Quantity (required, must be greater than 0)
   - Unit (required, e.g., kg, lbs, pieces)
   - Category (optional)
   - Notes (optional)
3. Click "Add Item" to save

### Editing Items

1. Click the "Edit" button on any inventory item card
2. Update the fields you want to change
3. Click "Update Item" to save changes

### Deleting Items

1. Click the "Delete" button on any inventory item card
2. Confirm the deletion in the popup dialog

### Filtering

1. Use the category dropdown to filter items by category
2. Select "All Categories" to view all items

## Technologies Used

- **React 18** - UI library
- **React Router v6** - Routing
- **Axios** - HTTP client
- **CSS3** - Styling with responsive design

## API Integration

The frontend uses Axios interceptors to:

- Automatically attach JWT tokens to authenticated requests
- Handle 401 unauthorized responses by redirecting to login
- Manage authentication state globally using React Context

## Features Highlights

### Responsive Design

- Mobile-friendly layout
- Adaptive grid system
- Touch-friendly buttons and forms

### User Experience

- Loading states for async operations
- Error handling and user feedback
- Form validation
- Confirmation dialogs for destructive actions
- Auto-redirect after authentication

### Security

- JWT token storage in localStorage
- Automatic token inclusion in API requests
- Token validation on app load
- Protected routes for authenticated users only

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Development Notes

- The application uses React functional components and hooks
- State management is handled with React Context API and local state
- All API calls are centralized in the `services/api.js` file
- Authentication state is managed globally via AuthContext

## Future Enhancements

Potential features to add:

- Search functionality
- Sort options (by name, quantity, date)
- Bulk operations
- Export data to CSV
- Image upload for items
- Barcode scanning
- Low stock alerts
- Shopping list generation
