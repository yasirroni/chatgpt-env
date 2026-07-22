using TOML

length(ARGS) == 1 || error("usage: warm_environment.jl ENVIRONMENT_DIR")
environment_dir = abspath(ARGS[1])
project_file = joinpath(environment_dir, "Project.toml")
isfile(project_file) || error("Project.toml not found: $project_file")

project = TOML.parsefile(project_file)
direct_dependencies = sort!(collect(keys(get(project, "deps", Dict{String, Any}()))))
skipped = Set(filter(item -> !isempty(item), split(get(ENV, "SKIP_LOAD_PACKAGES", ""), ',')))

failures = Pair{String, String}[]

for package in direct_dependencies
    if package in skipped
        println("SKIP ", package)
        continue
    end

    println("LOAD ", package)
    try
        Base.eval(Main, Meta.parse("using " * package))
    catch err
        message = sprint(showerror, err, catch_backtrace())
        push!(failures, package => message)
        println(stderr, "FAILED ", package)
        println(stderr, message)
    end
end

if !isempty(failures)
    println(stderr, "\nPackage load failures:")
    for (package, message) in failures
        first_line = first(split(message, '\n'))
        println(stderr, "- ", package, ": ", first_line)
    end
    exit(1)
end

println("Loaded ", length(direct_dependencies) - length(skipped), " direct dependencies.")
