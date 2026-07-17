const { createServer } = require('http');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');

// Pull existing client ID and secret from .env if available, or fallback to the provided ones
const envPath = path.resolve(process.cwd(), '.env');
let envContent = fs.existsSync(envPath) ? fs.readFileSync(envPath, 'utf8') : '';

const matchClientId = envContent.match(/YOUTUBE_CLIENT_ID=(.*)/);
const matchClientSecret = envContent.match(/YOUTUBE_CLIENT_SECRET=(.*)/);

const CLIENT_ID = matchClientId ? matchClientId[1].trim() : process.env.YOUTUBE_CLIENT_ID;
const CLIENT_SECRET = matchClientSecret ? matchClientSecret[1].trim() : process.env.YOUTUBE_CLIENT_SECRET;

if (!CLIENT_ID || !CLIENT_SECRET) {
  console.error("❌ Error: YOUTUBE_CLIENT_ID or YOUTUBE_CLIENT_SECRET is missing from .env");
  process.exit(1);
}
const REDIRECT_URI = 'http://localhost:3000/oauth2callback';

const SCOPES = 'https://www.googleapis.com/auth/youtube.readonly';

const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${CLIENT_ID}&redirect_uri=${REDIRECT_URI}&response_type=code&scope=${SCOPES}&access_type=offline&prompt=consent`;

const server = createServer(async (req, res) => {
  if (req.url.startsWith('/oauth2callback')) {
    const url = new URL(req.url, `http://localhost:3000`);
    const code = url.searchParams.get('code');
    
    if (code) {
      res.end('<h1>Authentication successful!</h1><p>You can safely close this tab and return to the terminal. The script has automatically updated your .env file.</p>');
      
      console.log('Received auth code:', code);
      
      try {
        const tokenRes = await fetch('https://oauth2.googleapis.com/token', {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: new URLSearchParams({
            code: code,
            client_id: CLIENT_ID,
            client_secret: CLIENT_SECRET,
            redirect_uri: REDIRECT_URI,
            grant_type: 'authorization_code'
          })
        });
        
        const tokens = await tokenRes.json();
        
        if (tokens.error) {
            console.error('❌ Error fetching tokens:', tokens);
            process.exit(1);
        }

        console.log('\n✅ Successfully received tokens!');
        
        // Update .env file
        if (envContent.includes('YOUTUBE_ACCESS_TOKEN=')) {
          envContent = envContent.replace(/YOUTUBE_ACCESS_TOKEN=.*/, `YOUTUBE_ACCESS_TOKEN=${tokens.access_token}`);
        } else {
          envContent += `\nYOUTUBE_ACCESS_TOKEN=${tokens.access_token}`;
        }
        
        if (tokens.refresh_token) {
          if (envContent.includes('YOUTUBE_REFRESH_TOKEN=')) {
            envContent = envContent.replace(/YOUTUBE_REFRESH_TOKEN=.*/, `YOUTUBE_REFRESH_TOKEN=${tokens.refresh_token}`);
          } else {
            envContent += `\nYOUTUBE_REFRESH_TOKEN=${tokens.refresh_token}`;
          }
        }
        
        fs.writeFileSync(envPath, envContent);
        console.log('✅ Updated .env with new tokens! You can now run the posting script.');
        
        server.close();
        process.exit(0);
      } catch (err) {
        console.error('❌ Failed to fetch token:', err);
        process.exit(1);
      }
    } else {
      res.end('<h1>Error: No authorization code found in the callback</h1>');
      server.close();
      process.exit(1);
    }
  }
});

server.listen(3000, () => {
  console.log('🌐 Starting local server on port 3000...');
  console.log('Opening your browser for YouTube authentication...');
  console.log(`If it doesn't open automatically, click here: \n\n${authUrl}\n`);
  
  const openCmd = process.platform === 'darwin' ? 'open' : process.platform === 'win32' ? 'start' : 'xdg-open';
  exec(`${openCmd} "${authUrl}"`);
});
