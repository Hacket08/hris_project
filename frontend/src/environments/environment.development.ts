export const environment = {
  production: false,
  apiBaseUrl: 'http://localhost:8011', // Non-Docker local dev (`ng serve` against a directly-run backend): 8001, this repo's documented/Docker Compose port, was occupied by an unrelated process on the machine this was verified on. Adjust to match wherever your backend is actually listening if 8001 is free for you.
};
