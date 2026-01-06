# resource "cloudflare_rate_limit" "api_limit" {
#   zone_id = var.cloudflare_zone_id
#   description = "Limit paste creation abuse"

#   threshold = 20
#   period    = 60

#   match = {
#     request = {
#       methods = ["POST"]
#       url =  "*/api/*"
#     }
#   }
#   action = {
#     mode = "block"
#     timeout = 60
#   }
# }

