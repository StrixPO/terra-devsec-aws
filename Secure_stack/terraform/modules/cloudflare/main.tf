resource "cloudflare_record" "frontend" {
  zone_id = var.cloudflare_zone_id
  name    = "psstbin.com"
  type    = "CNAME"
  value   = var.frontend_domain_name
  proxied = false
}