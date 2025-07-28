import express from 'express';
import helmet from 'helmet';
import cors from 'cors';
import compression from 'compression';
import rateLimit from 'express-rate-limit';
import { MongoClient, Db } from 'mongodb';
import webpush from 'web-push';
import cron from 'node-cron';
import dotenv from 'dotenv';
import { z } from 'zod';

// Load environment variables
dotenv.config();

// Configuration
const config = {
  port: process.env.PORT || 3001,
  mongoUri: process.env.MONGO_URI || 'mongodb://localhost:27017',
  dbName: process.env.DB_NAME || 'floridify',
  vapidPublicKey: process.env.VAPID_PUBLIC_KEY!,
  vapidPrivateKey: process.env.VAPID_PRIVATE_KEY!,
  vapidSubject: process.env.VAPID_SUBJECT || 'mailto:notifications@floridify.com',
  apiUrl: process.env.API_URL || 'http://localhost:8000',
  corsOrigins: process.env.CORS_ORIGINS?.split(',') || ['http://localhost:3000']
};

// Validate required environment variables
if (!config.vapidPublicKey || !config.vapidPrivateKey) {
  console.error('VAPID keys are required. Run npm run generate-vapid-keys to generate them.');
  process.exit(1);
}

// Configure web-push
webpush.setVapidDetails(
  config.vapidSubject,
  config.vapidPublicKey,
  config.vapidPrivateKey
);

// Schemas
const SubscriptionSchema = z.object({
  endpoint: z.string().url(),
  expirationTime: z.number().nullable().optional(),
  keys: z.object({
    p256dh: z.string(),
    auth: z.string()
  })
});

const PushSubscriptionSchema = z.object({
  subscription: SubscriptionSchema,
  userId: z.string().optional(),
  timezone: z.string().default('UTC'),
  preferences: z.object({
    wordOfDay: z.boolean().default(true),
    achievements: z.boolean().default(true),
    reminders: z.boolean().default(true)
  }).default({})
});

// Database connection
let db: Db;
let mongoClient: MongoClient;

async function connectToDatabase() {
  try {
    mongoClient = new MongoClient(config.mongoUri);
    await mongoClient.connect();
    db = mongoClient.db(config.dbName);
    console.log('Connected to MongoDB');
  } catch (error) {
    console.error('Failed to connect to MongoDB:', error);
    process.exit(1);
  }
}

// Express app setup
const app = express();

// Middleware
app.use(helmet());
app.use(cors({
  origin: config.corsOrigins,
  credentials: true
}));
app.use(compression());
app.use(express.json({ limit: '10mb' }));

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // Limit each IP to 100 requests per windowMs
  message: 'Too many requests from this IP, please try again later.'
});

app.use('/api/', limiter);

// Health check endpoint
app.get('/health', (_req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    uptime: process.uptime()
  });
});

// Get VAPID public key
app.get('/api/vapid-public-key', (_req, res) => {
  res.json({ publicKey: config.vapidPublicKey });
});

// Subscribe to notifications
app.post('/api/subscribe', async (req, res) => {
  try {
    console.log('Subscribe request body:', JSON.stringify(req.body, null, 2));
    
    const data = PushSubscriptionSchema.parse(req.body);
    
    // Store subscription in database
    const result = await db.collection('push_subscriptions').updateOne(
      { endpoint: data.subscription.endpoint },
      {
        $set: {
          ...data.subscription,
          userId: data.userId,
          timezone: data.timezone,
          preferences: data.preferences,
          createdAt: new Date(),
          updatedAt: new Date(),
          isActive: true
        }
      },
      { upsert: true }
    );
    
    console.log('Subscription stored:', result.upsertedId || 'updated existing');
    
    // Send welcome notification
    try {
      await webpush.sendNotification(
        data.subscription,
        JSON.stringify({
          title: 'Welcome to Floridify! 📚',
          body: 'You\'ll receive your first word tomorrow at 9 AM.',
          icon: '/icons/icon-192x192.png',
          badge: '/icons/badge-72x72.png',
          tag: 'welcome',
          data: {
            type: 'welcome',
            timestamp: new Date().toISOString()
          }
        })
      );
    } catch (error) {
      console.error('Failed to send welcome notification:', error);
    }
    
    res.status(201).json({ 
      message: 'Subscription successful',
      subscriptionId: result.upsertedId
    });
  } catch (error) {
    if (error instanceof z.ZodError) {
      res.status(400).json({ 
        error: 'Invalid subscription data',
        details: error.errors
      });
    } else {
      console.error('Subscription error:', error);
      res.status(500).json({ error: 'Failed to save subscription' });
    }
  }
});

// Unsubscribe from notifications
app.post('/api/unsubscribe', async (req, res) => {
  try {
    const { endpoint } = req.body;
    
    if (!endpoint) {
      return res.status(400).json({ error: 'Endpoint is required' });
    }
    
    const result = await db.collection('push_subscriptions').updateOne(
      { endpoint },
      { $set: { isActive: false, unsubscribedAt: new Date() } }
    );
    
    if (result.matchedCount === 0) {
      return res.status(404).json({ error: 'Subscription not found' });
    }
    
    res.json({ message: 'Unsubscribed successfully' });
  } catch (error) {
    console.error('Unsubscribe error:', error);
    res.status(500).json({ error: 'Failed to unsubscribe' });
  }
});

// Send notification to specific user
app.post('/api/send-notification', async (req, res) => {
  try {
    const { userId, notification } = req.body;
    
    if (!userId || !notification) {
      return res.status(400).json({ error: 'userId and notification are required' });
    }
    
    // Get user's subscriptions
    const subscriptions = await db.collection('push_subscriptions')
      .find({ userId, isActive: true })
      .toArray();
    
    if (subscriptions.length === 0) {
      return res.status(404).json({ error: 'No active subscriptions found for user' });
    }
    
    // Send to all user's devices
    const results = await Promise.allSettled(
      subscriptions.map(sub => 
        webpush.sendNotification(sub, JSON.stringify(notification))
          .catch(async (error) => {
            if (error.statusCode === 410) {
              // Subscription expired, mark as inactive
              await db.collection('push_subscriptions').updateOne(
                { endpoint: sub.endpoint },
                { $set: { isActive: false, expiredAt: new Date() } }
              );
            }
            throw error;
          })
      )
    );
    
    const successful = results.filter(r => r.status === 'fulfilled').length;
    const failed = results.filter(r => r.status === 'rejected').length;
    
    res.json({ 
      message: 'Notifications sent',
      successful,
      failed,
      total: results.length
    });
  } catch (error) {
    console.error('Send notification error:', error);
    res.status(500).json({ error: 'Failed to send notification' });
  }
});

// Test push notification endpoint
app.post('/api/test', async (req, res) => {
  try {
    const { endpoint } = req.body;
    
    if (!endpoint) {
      return res.status(400).json({ error: 'Endpoint is required' });
    }
    
    // Find subscription by endpoint
    const subscription = await db.collection('push_subscriptions')
      .findOne({ endpoint, isActive: true });
    
    if (!subscription) {
      return res.status(404).json({ error: 'Subscription not found' });
    }
    
    // Send test notification
    const testNotification = {
      title: 'Floridify Test Push',
      body: 'This notification was sent from the server! 🚀',
      icon: '/favicon-256.png',
      badge: '/favicon-128.png',
      tag: 'test-push',
      renotify: true,
      data: {
        type: 'test',
        timestamp: new Date().toISOString()
      }
    };
    
    await webpush.sendNotification(subscription, JSON.stringify(testNotification));
    
    res.json({ 
      message: 'Test notification sent successfully',
      subscription: { endpoint: subscription.endpoint }
    });
  } catch (error) {
    console.error('Test notification error:', error);
    res.status(500).json({ error: 'Failed to send test notification' });
  }
});

// Get word of the day from main API
async function getWordOfDay(): Promise<any> {
  try {
    const response = await fetch(`${config.apiUrl}/api/v1/word-of-day`);
    if (!response.ok) {
      throw new Error(`API returned ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Failed to fetch word of day:', error);
    // Fallback word if API fails
    return {
      word: 'serendipity',
      shortDefinition: 'the occurrence of events by chance in a happy way',
      definition: 'The occurrence and development of events by chance in a happy or beneficial way.'
    };
  }
}

// Schedule word of the day notifications
cron.schedule('0 9 * * *', async () => {
  console.log('Running word of the day notification job...');
  
  try {
    const word = await getWordOfDay();
    
    // Get all active subscriptions that want word of day
    const subscriptions = await db.collection('push_subscriptions')
      .find({ 
        isActive: true,
        'preferences.wordOfDay': { $ne: false }
      })
      .toArray();
    
    console.log(`Sending word of day to ${subscriptions.length} subscribers`);
    
    const notification = {
      title: '📖 Word of the Day',
      body: `${word.word}: ${word.shortDefinition}`,
      icon: '/icons/icon-192x192.png',
      badge: '/icons/badge-72x72.png',
      tag: 'word-of-day',
      data: {
        type: 'word-of-day',
        url: `/definition/${word.word}`,
        word: word.word,
        timestamp: new Date().toISOString()
      }
    };
    
    // Send in batches to avoid overwhelming the service
    const batchSize = 100;
    let successCount = 0;
    let failCount = 0;
    
    for (let i = 0; i < subscriptions.length; i += batchSize) {
      const batch = subscriptions.slice(i, i + batchSize);
      
      const results = await Promise.allSettled(
        batch.map(sub => 
          webpush.sendNotification(sub, JSON.stringify(notification))
            .catch(async (error) => {
              if (error.statusCode === 410) {
                // Subscription expired
                await db.collection('push_subscriptions').updateOne(
                  { endpoint: sub.endpoint },
                  { $set: { isActive: false, expiredAt: new Date() } }
                );
              }
              throw error;
            })
        )
      );
      
      successCount += results.filter(r => r.status === 'fulfilled').length;
      failCount += results.filter(r => r.status === 'rejected').length;
      
      // Small delay between batches
      if (i + batchSize < subscriptions.length) {
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    }
    
    console.log(`Word of day notifications sent: ${successCount} success, ${failCount} failed`);
    
    // Log statistics
    await db.collection('notification_logs').insertOne({
      type: 'word-of-day',
      word: word.word,
      timestamp: new Date(),
      totalSubscribers: subscriptions.length,
      successCount,
      failCount
    });
  } catch (error) {
    console.error('Word of day job failed:', error);
  }
});

// Cleanup expired subscriptions (daily at 2 AM)
cron.schedule('0 2 * * *', async () => {
  console.log('Running subscription cleanup job...');
  
  try {
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
    
    const result = await db.collection('push_subscriptions').deleteMany({
      isActive: false,
      $or: [
        { expiredAt: { $lt: thirtyDaysAgo } },
        { unsubscribedAt: { $lt: thirtyDaysAgo } }
      ]
    });
    
    console.log(`Cleaned up ${result.deletedCount} expired subscriptions`);
  } catch (error) {
    console.error('Cleanup job failed:', error);
  }
});

// Error handling
app.use((err: Error, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
  console.error('Unhandled error:', err);
  res.status(500).json({ 
    error: 'Internal server error',
    message: process.env.NODE_ENV === 'development' ? err.message : undefined
  });
});

// 404 handler
app.use((_req, res) => {
  res.status(404).json({ error: 'Not found' });
});

// Start server
async function start() {
  try {
    await connectToDatabase();
    
    const server = app.listen(config.port, () => {
      console.log(`Notification server running on port ${config.port}`);
      console.log(`Environment: ${process.env.NODE_ENV || 'development'}`);
      console.log(`CORS origins: ${config.corsOrigins.join(', ')}`);
    });
    
    // Graceful shutdown
    process.on('SIGTERM', async () => {
      console.log('SIGTERM received, shutting down gracefully...');
      
      server.close(() => {
        console.log('HTTP server closed');
      });
      
      await mongoClient.close();
      console.log('Database connection closed');
      
      process.exit(0);
    });
  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
}

// Start the server
start();