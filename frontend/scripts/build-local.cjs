const path = require('path');
const { spawnSync } = require('child_process');
const result = spawnSync(process.execPath, [require.resolve('react-scripts/bin/react-scripts'), 'build'], {
  stdio: 'inherit',
  env: { ...process.env, BUILD_PATH: path.resolve(__dirname, '../../backend/build') },
});
if (result.error) { console.error(result.error.message); process.exit(1); }
process.exit(result.status === null ? 1 : result.status);
