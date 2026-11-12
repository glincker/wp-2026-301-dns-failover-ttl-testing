# Claims behind GLINR-WP-2026-301

Every factual statement in the paper that rests on an outside source or on the experiments, with the wording the paper uses, the source and its access date (2026-11-11). Status VERIFIED means the source says what the wording says. Status PARTIAL means the wording is limited as stated: read the limit in the sentence. Author measurements are in `../experiments/results.md`; a row that cites an experiment id points there.

Claims: 81. Claims left out of the paper are listed in `excluded.md`.

## Chapter 1: A DNS answer is a cached copy

| ID | Status | Wording used in the paper | Source |
|---|---|---|---|
| C1-01 | VERIFIED | RFC 1034 says the TTL is a time limit on caching set by the zone administrator, and that it may be lowered before an anticipated change. | [RFC 1034, Domain Names: Concepts and Facilities](https://www.rfc-editor.org/rfc/rfc1034.html) (RFC 1034 section 3.6) |
| C1-03 | VERIFIED | RFC 2181 limits TTL to 0 through 2147483647, says a value with the most significant bit set is treated as zero, and describes TTL as a maximum time to live, not a mandatory one. | [RFC 2181, Clarifications to the DNS Specification](https://www.rfc-editor.org/rfc/rfc2181.html) (RFC 2181 section 8) |
| C1-06 | VERIFIED | RFC 1035 treats TTL as signed in one section and unsigned in another. | [RFC 1035, Domain Names: Implementation and Specification](https://www.rfc-editor.org/rfc/rfc1035.html) |
| C1-08 | VERIFIED | The summary gives 11:48 PM PDT on 19 October as the start of DNS failures, 2:25 AM for restored DNS information, and 2:40 AM as recovery after cached DNS records expired. | [AWS, Summary of the Amazon DynamoDB Service Disruption in the N. Virginia (us-east-1) Region](https://aws.amazon.com/message/101925/) |
| C1-09 | VERIFIED | Derived from the postmortem timestamps (label D): about 2 hours 52 minutes from first DNS failure to recovery, of which about 15 minutes followed the restoration of DNS data. | [AWS, Summary of the Amazon DynamoDB Service Disruption in the N. Virginia (us-east-1) Region](https://aws.amazon.com/message/101925/) |
| C1-10 | VERIFIED | The postmortem does not break down the tail after 2:25 AM into resolver caching and client behaviour. | [AWS, Summary of the Amazon DynamoDB Service Disruption in the N. Virginia (us-east-1) Region](https://aws.amazon.com/message/101925/) |
| C1-11 | PARTIAL | InfoQ quotes an engineer's view that DNS was the first symptom, not the root cause. | [InfoQ, AWS DynamoDB outage postmortem (Nov 15, 2025, Renato Losio)](https://www.infoq.com/news/2025/11/aws-dynamodb-outage-postmortem) |
| C1-12 | VERIFIED | Illustrative path. Each hop that caches has its own expiry (diagram claim, no number). | [systemd-resolved.service man page](https://www.freedesktop.org/software/systemd/man/latest/systemd-resolved.service.html); [Java SE 21 java.net.InetAddress, caching policy](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/net/InetAddress.html); [RFC 1034, Domain Names: Concepts and Facilities](https://www.rfc-editor.org/rfc/rfc1034.html) |
| C1-13 | VERIFIED | The systemd-resolved manual describes a caching and validating stub resolver whose caches are flushed on a network configuration change and on SIGHUP. | [systemd-resolved.service man page](https://www.freedesktop.org/software/systemd/man/latest/systemd-resolved.service.html) |

## Chapter 2: The five clocks

| ID | Status | Wording used in the paper | Source |
|---|---|---|---|
| C2-05 | VERIFIED | RFC 8767 requires a stale TTL above zero and recommends 30 seconds, suggests a 1.8 second client response timer, suggests a maximum stale time of 1 to 3 days, and says not to retry a failed refresh more often than every 30 seconds. | [RFC 8767, Serving Stale Data to Improve DNS Resiliency](https://www.rfc-editor.org/rfc/rfc8767.html) |
| C2-06 | VERIFIED | Moura et al. (IMC 2019) and RFC 9199 recommend at least 1 hour for general zones and say about 5 to 15 minutes only suits DNS load balancing or DDoS redirection. | [Moura, Heidemann, Schmidt, Hardaker. Cache Me If You Can: Effects of DNS Time-to-Live. IMC 2019. DOI 10.1145/3355369.3355568](https://par.nsf.gov/servlets/purl/10315383 (open copy)); [RFC 9199, Considerations for Large Authoritative DNS Server Operators](https://www.rfc-editor.org/rfc/rfc9199.html) (RFC 9199 section 3.5.2) |
| C2-07 | VERIFIED | Moura et al. found most resolvers child-centric and some parent-centric. | [Moura, Heidemann, Schmidt, Hardaker. Cache Me If You Can: Effects of DNS Time-to-Live. IMC 2019. DOI 10.1145/3355369.3355568](https://par.nsf.gov/servlets/purl/10315383 (open copy)) |
| C2-10 | VERIFIED | The Unbound manual online on 2026-11-11 lists these defaults. | [Unbound unbound.conf manual](https://unbound.docs.nlnetlabs.nl/en/latest/manpages/unbound.conf.html) |
| C2-11 | VERIFIED | The CoreDNS cache plugin documentation gives these defaults. | [CoreDNS cache plugin](https://coredns.io/plugins/cache/) |
| C2-12 | VERIFIED | The PowerDNS Recursor settings page gives these defaults. | [PowerDNS Recursor settings](https://doc.powerdns.com/recursor/settings.html) |
| C2-13 | VERIFIED | The dnsmasq manual states these limits and defaults. | [dnsmasq man page](https://thekelleys.org.uk/dnsmasq/docs/dnsmasq-man.html) |
| C2-14 | VERIFIED | Per their manuals, positive cache caps are 86400 s (Unbound, PowerDNS) and 3600 s (CoreDNS), negative caps 3600 s (Unbound, PowerDNS) and 1800 s (CoreDNS), and minimum floors 0 (Unbound), 1 s (PowerDNS override), 5 s (CoreDNS). | [Unbound unbound.conf manual](https://unbound.docs.nlnetlabs.nl/en/latest/manpages/unbound.conf.html); [CoreDNS cache plugin](https://coredns.io/plugins/cache/); [PowerDNS Recursor settings](https://doc.powerdns.com/recursor/settings.html); [dnsmasq man page](https://thekelleys.org.uk/dnsmasq/docs/dnsmasq-man.html) |
| C2-16 | VERIFIED | The BIND 9 reference lists these option names. | [BIND 9 Administrator Reference Manual, reference](https://bind9.readthedocs.io/en/latest/reference.html) |
| C2-17 | VERIFIED | In my lab Unbound 1.22.0 cached a 5 second record for about 5.3 s and a 20 second record for about 20.9 s with default settings. | Experiment E1, `experiments/results.md` |
| C2-18 | VERIFIED | In my lab BIND 9.20.30 cached a 5 second record for about 4.9 s and a 20 second record for about 20.1 s with default settings. | Experiment E1, `experiments/results.md` |
| C2-19 | VERIFIED | With a 15 second floor configured, a 5 second record was served from cache for about 15.2 s (Unbound) and about 14.5 s (BIND), and the first reply carried TTL 15. | Experiment E1, `experiments/results.md` |
| C2-20 | VERIFIED | With an 8 second cap configured, a 20 second record was cached for about 8.9 s (Unbound) and about 7.2 s (BIND). | Experiment E1, `experiments/results.md` |
| C2-21 | PARTIAL | In this lab each resolver landed within 0.9 s of the expected value on default, floor and cap behaviour (largest delta from expected 0.88 s, Unbound), and the two resolvers differed from each other by up to 1.67 s (8 s cap: Unbound 8.882 s, BIND 7.208 s; floor 0.64 s; 20 s record 0.79 s). | Experiment E1, `experiments/results.md` |
| C2-24 | PARTIAL | Moura et al. report that many resolvers apply a minimum caching time of tens of seconds. | [Moura, Heidemann, Schmidt, Hardaker. Cache Me If You Can: Effects of DNS Time-to-Live. IMC 2019. DOI 10.1145/3355369.3355568](https://par.nsf.gov/servlets/purl/10315383 (open copy)) |
| C2-25 | VERIFIED | Moura et al. report a median latency drop from 183 ms to 28.7 ms for a ccTLD after lengthening the TTL, and a controlled 60 s versus 86,400 s test from about 15,000 Atlas probes. | [Moura, Heidemann, Schmidt, Hardaker. Cache Me If You Can: Effects of DNS Time-to-Live. IMC 2019. DOI 10.1145/3355369.3355568](https://par.nsf.gov/servlets/purl/10315383 (open copy)) |
| C2-27 | VERIFIED | In my lab Unbound 1.22.0, polled once a second after the parent delegation moved to a new server, kept using the old server for about the child NS TTL (30.2 s with a parent TTL of 6 s and a child TTL of 30 s, 6.0 s with the values swapped). | Experiment E8, `experiments/results.md` |
| C2-28 | VERIFIED | In my lab BIND 9.20.30 switched to the new server after about the parent NS TTL (5.1 s with a parent TTL of 6 s and a child TTL of 30 s, 29.1 s with the values swapped). | Experiment E8, `experiments/results.md` |
| C2-29 | PARTIAL | In my lab, for a delegation change, Unbound 1.22.0 followed the child NS TTL and BIND 9.20.30 the parent NS TTL. | Experiment E8, `experiments/results.md` |

## Chapter 3: Negative caching and the record that does not exist yet

| ID | Status | Wording used in the paper | Source |
|---|---|---|---|
| C3-03 | VERIFIED | In my lab Unbound 1.22.0 cached an NXDOMAIN for about 8.6 s when SOA TTL and MINIMUM were 8 s, and for about 6.9 s when the SOA TTL was 30 s and the MINIMUM 6 s. | Experiment E2, `experiments/results.md` |
| C3-04 | VERIFIED | In my lab, when the test authoritative sent the authority-section SOA with TTL 6 (the lower of SOA TTL 30 and MINIMUM 6, as RFC 2308 section 5 expects of the responding server), BIND 9.20.30 cached the NXDOMAIN for about 5.9 s and Unbound 1.22.0 for about 6.9 s, first reply TTL 6 in both. | Experiment E2, `experiments/results.md` |
| C3-05 | VERIFIED | In my lab BIND 9.20.30 cached an NXDOMAIN for about 7.8 s with SOA TTL and MINIMUM 8 s. | Experiment E2, `experiments/results.md` |
| C3-06 | VERIFIED | With a 3 second negative cap configured, both resolvers stopped serving the NXDOMAIN after about 2.3 to 3.6 s although the SOA said 20 s. | Experiment E2, `experiments/results.md` |
| C3-07 | VERIFIED | In my lab a name created right after its NXDOMAIN stayed invisible to the resolver for roughly the negative TTL (rows C3-03, C3-05, C3-06). | Experiment E2, `experiments/results.md` |
| C3-09 | VERIFIED | The Java SE 21 InetAddress documentation says unsuccessful lookups are cached for 10 seconds by default, and a value of -1 means forever. | [Java SE 21 java.net.InetAddress, caching policy](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/net/InetAddress.html) |
| C3-10 | VERIFIED | Slack's engineering post says an NSEC for a wildcard omitted type information, causing some resolvers to cache "no records of any type" and fail A lookups for under 1 percent of users, over about 24 hours. | [Slack Engineering, What happened during Slack's DNSSEC rollout](https://slack.engineering/what-happened-during-slacks-dnssec-rollout/) |
| C3-12 | VERIFIED | In my lab, when the test authoritative sent an authority SOA with its full TTL (30 or 60 s) and a MINIMUM of 6 s, Unbound 1.22.0 still answered with TTL 6 and cached the NXDOMAIN for about 6.9 s. | Experiment E2, `experiments/results.md` |
| C3-13 | PARTIAL | In my lab, when the test authoritative sent an authority SOA with TTL 30 (or 60) and a MINIMUM of 6 s, a reply a compliant authoritative would not send, BIND 9.20.30 cached the NXDOMAIN for about 29.9 s (about 59.9 s) while Unbound cached it for about 6.9 s. | Experiment E2, `experiments/results.md` |

## Chapter 4: When the authoritative servers vanish

| ID | Status | Wording used in the paper | Source |
|---|---|---|---|
| C4-01 | VERIFIED | In my lab Unbound 1.22.0 answered from cache until the 5 second TTL ran out and then returned failures during an authoritative outage. | Experiment E3, `experiments/results.md` |
| C4-03 | VERIFIED | In my lab Unbound with serve-expired enabled and a 15 second window kept answering until about 20 s after the cache fill. | Experiment E3, `experiments/results.md` |
| C4-04 | PARTIAL | In my lab BIND 9.20.30 with serve-stale enabled and a 15 second max-stale-ttl last answered at about 19.0 s. | Experiment E3, `experiments/results.md` |
| C4-06 | VERIFIED | In my lab stale answers from BIND 9.20.30 carried a TTL of 30 s. | Experiment E3, `experiments/results.md` |
| C4-07 | PARTIAL | In my lab the probe's longest wait before a failure was about 6 s. | Experiment E3, `experiments/results.md` |
| C4-10 | VERIFIED | The CoreDNS documentation says serve_stale defaults to 1 hour and stale responses carry TTL 0. | [CoreDNS cache plugin](https://coredns.io/plugins/cache/) |
| C4-13 | VERIFIED | RFC 8767 notes that serving stale data can extend the time an attacker's forged data stays reachable and has DNSSEC implications. | [RFC 8767, Serving Stale Data to Improve DNS Resiliency](https://www.rfc-editor.org/rfc/rfc8767.html) (section 10) |
| C4-14 | VERIFIED | Meta's post says its DNS servers withdraw their BGP advertisements when they cannot reach the data centers, and that they became unreachable even though they were still operational. | [Meta Engineering, More details about the October 4 outage](https://engineering.fb.com/2021/10/05/networking-infrastructure/outage-details/) |
| C4-15 | VERIFIED | RFC 9520 cites query rates for .COM and .NET rising from about 7,000 to 900,000 per second during the October 2021 Facebook outage. | [RFC 9520, Negative Caching of DNS Resolution Failures](https://www.rfc-editor.org/rfc/rfc9520.html) (RFC 9520) |
| C4-16 | VERIFIED | RFC 9520 cites a 2021 test by Verisign with roughly 50 to 60,000 queries per second for one domain. | [RFC 9520, Negative Caching of DNS Resolution Failures](https://www.rfc-editor.org/rfc/rfc9520.html) |
| C4-18 | VERIFIED | Cloudflare's post gives these dates and times, notes DoH on separate hostname and IPs was largely unaffected, and says client retries created a spike after the fix. | [Cloudflare, 1.1.1.1 Resolver incident on July 14, 2025](https://blog.cloudflare.com/cloudflare-1-1-1-1-incident-on-july-14-2025/) |
| C4-21 | VERIFIED | Google's performance page says cache misses dominate latency and reports an average of about 130 ms for responding name servers and 300 to 400 ms including failures. | [Google Public DNS, Performance Benefits](https://developers.google.com/speed/public-dns/docs/performance) |

## Chapter 5: Failover by DNS: the arithmetic of cutover

| ID | Status | Wording used in the paper | Source |
|---|---|---|---|
| C5-01 | VERIFIED | Microsoft's documentation (page dated 2025-12-29, updated 2026-07-23 per its header) works through a 30 second interval, 3 tolerated failures, 10 second timeout and 30 second TTL, and marks the endpoint degraded after the fourth consecutive failure. | [Microsoft Learn, Azure Traffic Manager endpoint monitoring (page dated 2025-12-29, updated 2026-07-23 per page header)](https://learn.microsoft.com/en-us/azure/traffic-manager/traffic-manager-monitoring) |
| C5-06 | VERIFIED | Route 53's best practices document recommends 60 or 120 second TTLs for failover records, 1 hour to 1 day for NS and MX, and failover through data plane features. | [Amazon Route 53, Best practices for Route 53 DNS](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/best-practices-dns.html) |
| C5-07 | VERIFIED | In my lab a record with TTL 0 was not reused: the new answer appeared at once in both resolvers. | Experiment E4, `experiments/results.md` |
| C5-08 | VERIFIED | In my lab, after the authoritative answer changed, a resolver kept serving the old address for about the remaining TTL: measured minus expected stayed within 0.95 s for Unbound and within 0.72 s for BIND across TTLs of 3, 6 and 12 s. | Experiment E4, `experiments/results.md` |
| C5-09 | PARTIAL | In my lab Unbound's measured cutover was consistently 0.4 to 1 second above the remaining-TTL arithmetic, and BIND's was equal or slightly below. | Experiment E4, `experiments/results.md` |
| C5-10 | PARTIAL | A cutover estimate is the sum of detection time, change at the authoritative, the cache time at the resolver and client caches, and connection reuse; only the cache time term was measured (E4). | [Microsoft Learn, Azure Traffic Manager endpoint monitoring (page dated 2025-12-29, updated 2026-07-23 per page header)](https://learn.microsoft.com/en-us/azure/traffic-manager/traffic-manager-monitoring); [Amazon Route 53, How Route 53 determines whether a health check is healthy](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/dns-failover-determining-health-of-endpoints.html); Experiment E4, `experiments/results.md` |
| C5-13 | VERIFIED | RFC 8305 sets a 50 ms Resolution Delay and a default 250 ms Connection Attempt Delay (minimum 100 ms, maximum 2 s) and staggers connection attempts. | [RFC 8305, Happy Eyeballs Version 2](https://www.rfc-editor.org/rfc/rfc8305.html) |
| C5-14 | VERIFIED | AWS's summary says Network Load Balancer health checks flapped and automatic AZ failover removed capacity, which AWS disabled at 9:36 AM and re-enabled at 2:09 PM, with the overall event ending at 2:20 PM on 20 October. | [AWS, Summary of the Amazon DynamoDB Service Disruption in the N. Virginia (us-east-1) Region](https://aws.amazon.com/message/101925/) |
| C5-17 | VERIFIED | In my lab, when the first of two addresses refused the connection, Python, Go (both resolver modes) and curl connected to the second address within about a quarter of a second. | Experiment E7, `experiments/results.md` |
| C5-18 | PARTIAL | In my lab a Java HttpURLConnection client given two addresses, the first refusing connections, failed with a ConnectException instead of using the second address. | Experiment E7, `experiments/results.md` |
| C5-19 | PARTIAL | In my lab a Java HttpURLConnection client given two addresses, the first dropping all SYNs, gave up with a timeout instead of using the second address. | Experiment E7, `experiments/results.md` |
| C5-20 | VERIFIED | In my lab Python (urllib, 3 s timeout) tried the second address after the full connect timeout, so the request succeeded after about 3 seconds. | Experiment E7, `experiments/results.md` |
| C5-21 | PARTIAL | In my lab Python with no connect timeout set and the first of two addresses blackholed had not connected to the live address within 20 seconds. | Experiment E7, `experiments/results.md` |
| C5-22 | VERIFIED | In my lab, with the first of two addresses blackholed, Go reached the live address after about 2 s with a 3 s connect timeout and about 15 s with none set, and curl after about 2.5 s and about 11 s. | Experiment E7, `experiments/results.md` |
| C5-23 | VERIFIED | In my lab Go (both resolver modes) and curl, given a dead IPv6 address and a live IPv4 address, connected to the IPv4 address within about 0.3 seconds even when the IPv6 address silently dropped packets. | Experiment E7, `experiments/results.md` |
| C5-24 | VERIFIED | In my lab Python (urllib, glibc getaddrinfo) showed no Happy Eyeballs behavior: with a blackholed IPv6 address it waited for the connect timeout. | Experiment E7, `experiments/results.md` |
| C5-25 | PARTIAL | In my lab a Java HttpURLConnection client connected to the live IPv4 address within 0.02 s in the dual stack cases. | Experiment E7, `experiments/results.md` |

## Chapter 6: Clients that ignore your TTL

| ID | Status | Wording used in the paper | Source |
|---|---|---|---|
| C6-01 | VERIFIED | The Java SE 21 InetAddress documentation says positive results are cached forever when a security manager is installed and otherwise for an implementation dependent time, with negative results cached 10 seconds by default. | [Java SE 21 java.net.InetAddress, caching policy](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/net/InetAddress.html) |
| C6-03 | PARTIAL | Microsoft's documentation says existing connections are not affected by DNS changes. | [Microsoft Learn, Azure Traffic Manager endpoint monitoring (page dated 2025-12-29, updated 2026-07-23 per page header)](https://learn.microsoft.com/en-us/azure/traffic-manager/traffic-manager-monitoring) |
| C6-05 | VERIFIED | In my lab, with a 20 second TTL, lowering the TTL to 2 seconds right before the change barely helped (stale window about 18 to 19 s), while lowering it one old TTL ahead cut the window to about 2 s (Unbound) and under 1 s (BIND). | Experiment E5, `experiments/results.md` |
| C6-06 | VERIFIED | A June 2026 dev.to post (date inferred, not stated on the page) says resolvers floor TTLs at typically 30 to 60 seconds and cites no measurement. | [dev.to, DNS TTL Best Practices: How to Choose the Right Values (dnsassistant)](https://dev.to/dnsassistant/dns-ttl-best-practices-how-to-choose-the-right-values-4jni) |
| C6-08 | VERIFIED | The Kubernetes DNS documentation shows an example pod resolv.conf with three search domains and options ndots:5. | [Kubernetes, DNS for Services and Pods](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/) |
| C6-11 | VERIFIED | In my lab, Python, Go (both resolver modes) and a new curl process per request moved to the new address within about 2.5 s of the record change, in step with the resolver's 2 second TTL, with no client-side cache holding the old one. | Experiment E6, `experiments/results.md` |
| C6-12 | VERIFIED | In my lab OpenJDK 21.0.13 with HttpURLConnection and default settings kept using the old address for about 30 seconds after the first lookup although the record TTL was 2 seconds. | Experiment E6, `experiments/results.md` |
| C6-13 | VERIFIED | In my lab OpenJDK 21.0.13 with networkaddress.cache.ttl set to 5 held the old address for about 5 seconds after the first lookup, and with the property set to 0 it followed the resolver's 2 second TTL. | Experiment E6, `experiments/results.md` |
| C6-14 | VERIFIED | In my lab OpenJDK 21.0.13 with networkaddress.cache.ttl set to -1 kept using the old address for the whole 45 second run and never switched. | Experiment E6, `experiments/results.md` |
| C6-15 | VERIFIED | In my lab a long-lived curl process, sending one request per half second through its own DNS cache, kept using the old address until about 55.7 seconds after the change, while a new curl process per request moved within about 1.8 seconds. | Experiment E6, `experiments/results.md` |

## Chapter 7: Split-horizon, search lists and delegation traps

| ID | Status | Wording used in the paper | Source |
|---|---|---|---|
| C7-03 | VERIFIED | Slack's post says the DS record was cached (the .com TTL asks for 24 hours, and Slack observed Google Public DNS capping it at 6 hours), so rolling back caused SERVFAIL at validating resolvers. | [Slack Engineering, What happened during Slack's DNSSEC rollout](https://slack.engineering/what-happened-during-slacks-dnssec-rollout/) |

## Chapter 8: Automation that writes DNS

| ID | Status | Wording used in the paper | Source |
|---|---|---|---|
| C8-01 | VERIFIED | AWS's summary describes the delayed Enactor, the cleanup of the old plan, the inconsistent state that blocked later plans, manual repair, and the disabling of the Planner and Enactor automation worldwide until fixed. | [AWS, Summary of the Amazon DynamoDB Service Disruption in the N. Virginia (us-east-1) Region](https://aws.amazon.com/message/101925/) |

## Chapter 9: Runbook: TTL policy, change plan, monitoring

| ID | Status | Wording used in the paper | Source |
|---|---|---|---|
| C9-01 | VERIFIED | Policy ranges follow RFC 9199 and Moura et al. (at least 1 hour for general zones) and Route 53 guidance (60 or 120 s for failover records). | [RFC 9199, Considerations for Large Authoritative DNS Server Operators](https://www.rfc-editor.org/rfc/rfc9199.html); [Amazon Route 53, Best practices for Route 53 DNS](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/best-practices-dns.html); [Moura, Heidemann, Schmidt, Hardaker. Cache Me If You Can: Effects of DNS Time-to-Live. IMC 2019. DOI 10.1145/3355369.3355568](https://par.nsf.gov/servlets/purl/10315383 (open copy)) |
| C9-02 | VERIFIED | In my lab, lowering the TTL only at the moment of change left the stale window near the old TTL, while lowering a full old TTL ahead shortened it to about 1 to 2.3 s (E5). RFC 1034 also advises lowering before an anticipated change. | Experiment E5, `experiments/results.md`; [RFC 1034, Domain Names: Concepts and Facilities](https://www.rfc-editor.org/rfc/rfc1034.html) |
| C9-03 | VERIFIED | In my lab, the record stayed invisible for the negative TTL after a failed lookup (C3-07), so check the SOA negative TTL first. | Experiment E2, `experiments/results.md`; [RFC 2308, Negative Caching of DNS Queries](https://www.rfc-editor.org/rfc/rfc2308.html) |
