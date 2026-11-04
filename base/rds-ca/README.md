# RDS CA bundle

`global-bundle.pem` is the public certificate bundle AWS publishes for Amazon RDS, downloaded from
`https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem`. It contains only public CA certificates (no keys, no
account or region data). The backend and the migration Job trust it through `NODE_EXTRA_CA_CERTS`, so the TLS
connection to RDS is both encrypted and **verified** (`sslmode=require` in the pg library verifies the chain and host).

Refresh it when AWS rotates the RDS CAs: download the file again from the URL above, compare the certificate count and
subjects, and commit the change like any other. AWS does not publish a checksum next to the file.
