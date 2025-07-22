# Modern Docker SSL/HTTPS Deployment on AWS EC2 (2024-2025)

## Executive Summary

Based on recent research from 2024-2025, here are the key findings for deploying Dockerized applications to AWS EC2 with SSL/HTTPS:

## 1. Nginx Reverse Proxy with Let's Encrypt

### Best Practice Architecture
- **Separate containers**: Run nginx and certbot in separate containers with shared volumes
- **Auto-renewal**: Configure certbot to run renewal checks every 12 hours
- **Nginx reload**: Configure nginx to reload configuration every 6 hours to pick up renewed certificates

### Recommended Solution: JonasAlfredsson/docker-nginx-certbot
The most popular and well-maintained solution combines nginx and certbot in a single image with automatic renewal:

```yaml
version: '3'
services:
  nginx:
    image: jonasal/nginx-certbot:latest
    restart: unless-stopped
    environment:
      - CERTBOT_EMAIL=your@email.com
    ports:
      - 80:80
      - 443:443
    volumes:
      - nginx_secrets:/etc/letsencrypt
      - ./user_conf.d:/etc/nginx/user_conf.d
volumes:
  nginx_secrets:
```

## 2. Certbot Integration with Docker

### Key Requirements
- **Domain**: Must have a valid FQDN pointing to EC2 instance public IP
- **Security Groups**: Allow inbound traffic on ports 80 and 443
- **Volume Mounts**: 
  - `/etc/letsencrypt`: Certificate storage
  - `/var/www/certbot`: ACME challenge directory

### Auto-Renewal Strategies
1. **Container-based**: Certbot runs as a service with entrypoint loop
2. **System-based**: On Amazon Linux 2023, use `certbot-renew.timer` systemd service
3. **Best practice**: Renew 30 days before expiry (certificates valid for 90 days)

## 3. SSL Certificate Auto-Renewal

### Production Configuration
```yaml
services:
  certbot:
    image: certbot/certbot
    volumes:
      - ./certbot/conf:/etc/letsencrypt
      - ./certbot/www:/var/www/certbot
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"
    
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./certbot/conf:/etc/letsencrypt
      - ./certbot/www:/var/www/certbot
    command: "/bin/sh -c 'while :; do sleep 6h & wait $${!}; nginx -s reload; done & nginx -g \"daemon off;\"'"
```

## 4. ALB vs Nginx SSL Termination

### Use AWS ALB When:
- Need tight AWS integration (ACM, WAF)
- Simple certificate management (under ALB limits)
- High availability and fault tolerance required
- Cost: ~$22.88/month minimum

### Use Nginx When:
- Managing many SSL certificates (ALB has limits)
- Multi-cloud or hybrid deployments
- Need advanced features (caching, custom routing)
- More control over SSL configuration

### Hybrid Approach (Recommended for Production)
- Use Network Load Balancer (NLB) in TCP passthrough mode
- Terminate SSL at nginx level
- Benefit from AWS infrastructure + nginx flexibility

## 5. Docker Deployment Strategies on EC2

### Container Deployment Options
1. **Direct Docker on EC2**: Simple but requires manual management
2. **ECS on EC2**: Better orchestration, task isolation limitations
3. **EKS on EC2**: Full Kubernetes features, more complex

### Best Practices
- Use **awsvpc** network mode for security group assignment
- Keep containers in private subnets
- Use NAT Gateway or PrivateLink for outbound traffic
- Enable EBS encryption for Docker volumes

## 6. GitHub Actions CI/CD Pipeline

### Essential Configuration
```yaml
name: Deploy to EC2
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v1
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          
      - name: Login to Amazon ECR
        run: |
          aws ecr get-login-password --region us-east-1 | 
          docker login --username AWS --password-stdin $ECR_REGISTRY
          
      - name: Build and push Docker image
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
          
      - name: Deploy to EC2
        run: |
          ssh -o StrictHostKeyChecking=no ec2-user@$EC2_HOST \
            "docker pull $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG && 
             docker-compose up -d"
```

## 7. Security Groups and Networking

### Required Security Group Rules
```yaml
Inbound Rules:
  - Port 22 (SSH): Your IP only
  - Port 80 (HTTP): 0.0.0.0/0
  - Port 443 (HTTPS): 0.0.0.0/0
  
Outbound Rules:
  - All traffic: 0.0.0.0/0 (default)
```

### Network Architecture
- Place application containers in private subnets
- Use ALB/NLB in public subnets
- Configure VPC endpoints for AWS services
- Enable VPC Flow Logs for monitoring

## 8. Production Best Practices

### SSL/TLS Configuration
- Use TLS 1.2 and 1.3 only
- Disable older SSL/TLS versions
- Configure strong cipher suites
- Enable HSTS headers

### Container Security
- Scan images for vulnerabilities
- Use minimal base images
- Run containers as non-root
- Implement resource limits

### Secrets Management
- Use AWS Secrets Manager or Parameter Store
- Never hardcode credentials
- Rotate secrets regularly
- Use IAM roles for AWS access

### Monitoring and Logging
- CloudWatch for container logs
- VPC Flow Logs for network traffic
- Set up alerts for certificate expiry
- Monitor container health checks

## Initial Setup Checklist

1. **Domain Setup**
   - [ ] Register domain or configure existing
   - [ ] Create A record pointing to EC2 IP
   - [ ] Consider Elastic IP for production

2. **EC2 Configuration**
   - [ ] Launch EC2 instance (t3.medium or larger)
   - [ ] Configure security groups
   - [ ] Install Docker and Docker Compose
   - [ ] Set up SSH key access

3. **SSL Setup**
   - [ ] Choose SSL strategy (ALB vs Nginx)
   - [ ] Configure CERTBOT_EMAIL
   - [ ] Test with Let's Encrypt staging
   - [ ] Switch to production certificates

4. **CI/CD Pipeline**
   - [ ] Set up GitHub Actions secrets
   - [ ] Configure ECR repository
   - [ ] Create deployment workflow
   - [ ] Test automated deployments

5. **Monitoring**
   - [ ] Enable CloudWatch logging
   - [ ] Set up certificate expiry alerts
   - [ ] Configure health checks
   - [ ] Implement backup strategy

## Cost Considerations

- **ALB**: ~$22.88/month + data transfer
- **EC2**: Varies by instance type
- **Data Transfer**: $0.09/GB out
- **EBS Storage**: $0.10/GB-month
- **Certificates**: Free with Let's Encrypt

## Conclusion

For most production deployments in 2024-2025, the recommended approach is:
1. Use nginx with certbot for SSL termination
2. Deploy with Docker Compose on EC2
3. Automate with GitHub Actions
4. Consider NLB for high-traffic scenarios
5. Implement comprehensive security measures

This provides a balance of flexibility, cost-effectiveness, and production readiness while leveraging modern DevOps practices.