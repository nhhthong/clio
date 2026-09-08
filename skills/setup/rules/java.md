---
paths:
  - "**/*.java"
  - "**/*.kt"
---
# Java / Kotlin (JVM)
<!-- Clio starter — /clio:setup step 4. Verify every line against this repo, delete lines that
     don't hold here, delete the whole file if the repo has no JVM code. Keep it under 20 lines. -->

- Build and test through the wrapper the repo ships: `./mvnw -q test` or `./gradlew test`. Never edit `target/` or `build/`.
- Formatter: whatever the build configures (spotless, google-java-format, ktlint, checkstyle) — run the build's format goal, never hand-format.
- Generated — edit the annotated source / `.proto` / OpenAPI spec, never the output under `target/generated-sources/` or `build/generated/`: Lombok accessors, MapStruct `*Impl`, JPA `*_` metamodel, protobuf, generated API clients.
- Spring: constructor injection only, no field `@Autowired`; `@Transactional` on the service layer, never on controllers; DTOs at the controller boundary, entities never leave the service.
- Money: `BigDecimal` with explicit scale and `RoundingMode`; never `double`.
- Time: `java.time` only; store UTC, convert at the edge.
- Flyway/Liquibase: an applied migration is frozen — new versioned file, never edit an applied one.
