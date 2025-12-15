```
curl http://localhost/dependency-service/projects -X POST -d '{"repo_url":"http://git-server:8000/advanced-proofs","commit":"3218801d0debaf62349ffc2dd71202bcf8a2ba92"}' -H "Content-Type: application/json" | jq
```

```
curl http://localhost/dependency-service/projects -X POST -d '{"repo_url":"http://git-server:8000/advanced-proofs","commit":"3218801d0debaf62349ffc2dd71202bcf8a2ba92"}' -H "Content-Type: application/json" | jq
```

```
wget http://localhost/pdf-service/aHR0cDovL2dpdC1zZXJ2ZXI6ODAwMC9hZHZhbmNlZC1wcm9vZnM=/3218801d0debaf62349ffc2dd71202bcf8a2ba92/main.pdf
```