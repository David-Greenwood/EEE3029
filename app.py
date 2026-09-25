import streamlit as st
import cvxpy as cp
import numpy as np
import plotly.graph_objects as go
import pandas as pd

# Helper function for plots on tabs 2 and 3
def add_branch(fig, start, end, flow, limit):

#Set colour based on flow level
    loading = abs(flow) / limit

    if loading < 0.8:
        colour = "green"
    elif loading < 1.0:
        colour = "orange"
    else:
        colour = "red"

    width = 2 + 8 * loading

    # Direction
    if flow >= 0:
        x0, y0 = pos[start]
        x1, y1 = pos[end]
    else:
        x0, y0 = pos[end]
        x1, y1 = pos[start]

        # Line
    fig.add_trace(  
        go.Scatter(
            x=[x0, x1],
            y=[y0, y1],
            mode="lines",
            line=dict(
                color=colour,
                width=width
            ),
            hoverinfo="skip",
            showlegend=False
        )
    )
        # Arrow
    fig.add_annotation(

        x=x1,
        y=y1,
        ax=x0,
        ay=y0,
        xref="x",
        yref="y",
        axref="x",
        ayref="y",
        showarrow=True,
        arrowhead=3,
        arrowsize=1.5,
        arrowwidth=width/2,
        arrowcolor=colour
        )

     # Flow label
    xm = (x0 + x1) / 2
    ym = (y0 + y1) / 2

    fig.add_annotation(
        x=xm,
        y=ym,
        text=f"{abs(flow):.1f} MW",
        showarrow=False,
        bgcolor="white"
        )
    
#Create different tabs for each example
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Economic Dispatch", "Interconnector Constraint", "Optimal Powerflow", "Net-Zero Planning", "Energy Storage","Variable Renewable Energy"])

#Tab 1, which shows economic dispatch of two generators
with tab1:

    #Image showing the basic setup.
    st.image("ED.png", width=600)
    # Inputs
    demand = st.slider("Demand (MW)", 100, 1000, 600)

    #Create two columns, each with three sliders to set the generator cost parameters
    col1, col2 = st.columns(2,gap="small")

    with col1:
        a1 = st.slider("Generator 1 Linear cost",10,50,30)
        b1 = st.slider("Generator 1 Quadratic cost",0.01,0.2,0.05)
        c1 = st.slider("Generator 1 Fixed cost",100,500,300)

    with col2:
        a2 = st.slider("Generator 2 Linear cost",10,50,30)
        b2 = st.slider("Generator 2 Quadratic cost",0.01,0.2,0.05)
        c2 = st.slider("Generator 2 Fixed cost",100,500,300)

    #Checkbox and if statement to set generator minimum output to 0 (or not)
    NegGen = st.checkbox("Allow Negative Generation?")

    if NegGen:
        Pg1 = cp.Variable(nonneg=False)
        Pg2 = cp.Variable(nonneg=False)
    else:
        Pg1 = cp.Variable(nonneg=True)
        Pg2 = cp.Variable(nonneg=True)


    # Objective = C1 + P1 x a1 + P1^2 x b1 + c2 + p2 x a2 + p2^2 x b2
    cost = (
        c1 + a1*Pg1 + b1*Pg1**2 +
        c2 + a2*Pg2 + b2*Pg2**2
    )

    # Constraints (Power balance)
    constraint = (Pg1 + Pg2 == demand)
    

    # Solve the optimisation
    prob = cp.Problem(cp.Minimize(cost), [constraint])
    prob.solve()

    # Print results to screen
    st.metric("Generator 1", f"{Pg1.value:.1f} MW")
    st.metric("Generator 2", f"{Pg2.value:.1f} MW")
    st.metric("Cost", f"£{prob.value:.0f}/h")
    st.metric("Shadow Price", f"{-constraint.dual_value:.1f} £/MWh")

    #Calculate marginal cost curves for plotting
    P = np.linspace(0, max(Pg1.value,Pg2.value)+100, 200)

    MC1 = a1 + 2*b1 * P
    MC2 = a2 + 2*b2 * P
    #Figure which visualises how the solution sets both marginal costs to the same value
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=P,
            y=MC1,
            name="Generator 1",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=P,
            y=MC2,
            name="Generator 2"
        )
    )

    fig.add_hline(
        y=-constraint.dual_value,
        line_dash="dash",
        annotation_text=f"λ = {-constraint.dual_value:.1f}"
    )

    fig.add_vline(
        x = Pg1.value,
        line_dash="dash",
        annotation_text=f"PG1 = {Pg1.value:.1f} MW"

    )

    fig.add_vline(
        x = Pg2.value,
        line_dash="dash",
        annotation_text=f"PG2 = {Pg2.value:.1f} MW"

    )

    fig.update_layout(
        xaxis_title="Generator Output (MW)",
        yaxis_title="Marginal Cost (£/MWh)"
    )
   
    st.plotly_chart(fig, use_container_width=True)
    
#Tab 2 shows two systems connected by a transmisison line.
with tab2:

    #Prints an image of the interconnected system to the screen
    st.image("Interconnector.png", width=600)

    #Sliders to set the demand in each system and the interconnector capacity
    demand1 = st.slider("System 1 Demand",100,1000,500)
    demand2 = st.slider("System 2 Demand",100,1000,500)
    ICcap = st.slider("Interconnector Capacity (MW)",0,1000,0)

    # Variables - The power from each generator and the flow along the interconnector
    Pgs1 = cp.Variable(nonneg=True)
    Pgs2 = cp.Variable(nonneg=True)
    F = cp.Variable(nonneg = False)

    #Objective function which comprises two cost functions (fixed in this example)
    cost2 = (
            300 + 30*Pgs1 + 0.03*Pgs1**2 +
            200 + 20*Pgs2 + 0.02*Pgs2**2
        )
    
    # Constraints - power balance at each node (constraints 1 and 2) and the flow on the interconnector (3 and 4)
    constraint1 = (Pgs1 - F == demand1)
    constraint2 = (Pgs2 + F == demand2)
    constraint3 = (F <= ICcap)
    constraint4 = (F >= -ICcap)
        
    # Solve
    prob2 = cp.Problem(cp.Minimize(cost2), [constraint1,constraint2,constraint3,constraint4])
    prob2.solve()

    #Extract results from optimization for plotting
    ICFlow = F.value
    Price_S1 = -constraint1.dual_value
    Price_S2 = -constraint2.dual_value
    
    #This creates a plot of the system visualising the flow, dispatch, and costs at each bus
    # Bus coordinates
    pos = {
        'B1': (-1, 0),
        'B2': (1, 0)
    }
    
    fig_IC = go.Figure()
    add_branch(fig_IC, 'B1', 'B2', F.value, ICcap)
    # Buses
    bus_x = [pos['B1'][0], pos['B2'][0]]
    bus_y = [pos['B1'][1], pos['B2'][1]]

    bus_text = [
    f"System 1<br>G1 = {Pgs1.value:.0f} MW <br> D1 = {demand1:.0f} MW <br> Price = {Price_S1:.1f} £/MWh",
    f"System 2<br>G2 = {Pgs2.value:.0f} MW <br> D2 = {demand2:.0f} MW <br> Price = {Price_S2:.1f} £/MWh"
    ]
    fig_IC.add_trace(
            go.Scatter(
                x=bus_x,
                y=bus_y,
                mode="markers+text",
                text=bus_text,
                textposition="top center",
                marker=dict(
                    size=35,
                    color="lightblue",
                    line=dict(color="black", width=2)
                ),
                showlegend=False
            )
        )
    st.plotly_chart(fig_IC, use_container_width=True)    

#Tab 3 is a simple optimal power flow example on a 3 bus network
with tab3: 

    #Print an image of the system
    st.image("OPF.png", width=600)

    #Slider to set the system demand
    demandb3 = st.slider("Bus 3 Demand",100,1000,500)

    #Create two columns to set the network parameters
    col1a,col2a = st.columns(2)

    #Sliders to set the reactances 
    with col1a: 
        X12 = st.slider("X\u2081\u2082",0.1,0.5,0.3)
        X13 = st.slider("X\u2081\u2083",0.1,0.5,0.3)
        X23 = st.slider("X\u2082\u2083",0.1,0.5,0.3)

    #SLiders to set the line limits
    with col2a:
        P12Lim = st.slider("Line 1-2 Limit (MW)",100,1000,500)
        P13Lim = st.slider("Line 1-3 Limit (MW)",100,1000,500)
        P23Lim = st.slider("Line 2-3 Limit (MW)",100,1000,500)

    # Variables for the optimization - generators and line flows
    Pgb1 = cp.Variable(nonneg=True)
    Pgb2 = cp.Variable(nonneg=True)
    P12 = cp.Variable(nonneg=False)
    P13 = cp.Variable(nonneg=False)
    P23 = cp.Variable(nonneg=False)
    
    #Objective function summing generator cost functions
    cost3 = (
            300 + 30*Pgb1 + 0.03*Pgb1**2 +
            200 + 20*Pgb2 + 0.02*Pgb2**2
        )
        
        # Constraints - power balance for the system, line flows based on super position, and line limits
        #This is formulated the same way it would be solved by hand. Future versions could allow alternative formulations.
    opfconstraints = [Pgb1 + Pgb2 == demandb3,
        P12 == Pgb1*(X13/(X12+X13+X23)) - Pgb2*(X23/(X12+X13+X23)),
        P13 == Pgb1*((X12+X23)/(X12+X13+X23)) + Pgb2*((X23)/(X12+X13+X23)),
        P23 == Pgb1*((X12+X23)/(X12+X13+X23)) + Pgb2*((X13+X12)/(X12+X13+X23)),
        P12 <= P12Lim,
        P12 >= -P12Lim,
        P13 <= P13Lim,
        P13 >= -P13Lim,
        P23 <= P23Lim,
        P23 >= -P23Lim]
            
        # Solve
    prob3 = cp.Problem(cp.Minimize(cost3), opfconstraints)
    prob3.solve()

    #If statement to plot the results (if successful) or show an infeasibility message (if not)
    if prob3.status in ["optimal", "optimal_inaccurate"]:

        st.metric("Generator 1", f"{Pgb1.value:.1f} MW")
        st.metric("Generator 2", f"{Pgb2.value:.1f} MW")
        st.metric("Line 1-2 Flow", f"{P12.value:.1f} MW")
        st.metric("Line 1-3 Flow", f"{P13.value:.1f} MW")
        st.metric("Line 2-3 Flow", f"{P23.value:.1f} MW")
        st.metric("Cost", f"£{prob3.value:.0f}/h")

        #Plot a network diagram visualising flows
        # Bus coordinates
        pos = {
            'B1': (-1, 1),
            'B2': (1, 1),
            'B3': (0, 0)
        }
        
        fig_opf = go.Figure()
                        
            # Branches
        add_branch(fig_opf, 'B1', 'B2', P12.value, P12Lim)
        add_branch(fig_opf, 'B1', 'B3', P13.value, P13Lim)
        add_branch(fig_opf, 'B2', 'B3', P23.value, P23Lim)
        
        # Buses
        bus_x = [pos['B1'][0], pos['B2'][0], pos['B3'][0]]
        bus_y = [pos['B1'][1], pos['B2'][1], pos['B3'][1]]
        
        bus_text = [
            f"Bus 1<br>G1 = {Pgb1.value:.0f} MW",
            f"Bus 2<br>G2 = {Pgb2.value:.0f} MW",
            f"Bus 3<br>D = {demandb3:.0f} MW"
        ]
        
        fig_opf.add_trace(
            go.Scatter(
                x=bus_x,
                y=bus_y,
                mode="markers+text",
                text=bus_text,
                textposition="top center",
                marker=dict(
                    size=35,
                    color="lightblue",
                    line=dict(color="black", width=2)
                ),
                showlegend=False
            )
        )
        
        fig_opf.update_layout(
            title="3-Bus Network",
            xaxis=dict(
                visible=False
            ),
            yaxis=dict(
                visible=False
            ),
            plot_bgcolor="white",
            margin=dict(l=20, r=20, t=50, b=20),
            height=600
        )
        
        fig_opf.update_yaxes(
            scaleanchor="x",
            scaleratio=1
        )
        st.plotly_chart(fig_opf, use_container_width=True)    

       
      #Message for infeasible solution
    else:
        st.text("Problem Infeasible - try increasing line limit, decreasing demand, or changing network parameters")

    #Tab 4 shows an system planning example
    with tab4:

        #Sliders to set the demand in terms of peak and overall demand
        Peak = st.slider("Peak Demand (MW)",500, 2000, 1000 )
        LF = st.slider("Load Factor (%)",10,100,30)
        Energy = 8760*Peak*LF/100
        st.metric("Annual Energy Demand", f"{Energy/1000} GWh")

        #Technology are in an editable data frame which is displayed as a table
        Technologies_base = pd.DataFrame(
            {
                "Solar": [0, 5, 0, 0, 15,60,10,0],
                "Wind": [5, 25, 0, 0, 35,100,20,0],
                "CCGT Gas": [70, 90, 6, 450, 90,80,10,10],
                "Nuclear": [20, 85, 5, 0, 90,250,10,50],
            },
            index = ["Energy Cost £/MWh", "Derating Factor (%)", "Inertia Contant (GW.s/GW)", "Carbon Intensity (kgCO\u2082/kWh)", "Capacity Factor (%)", "Capital Cost (£k/MW)", "Site Scarcity Cost (£/MW\u00b2)","Minimum Load Factor (%)"]
        )

        #Display the editable table
        Technologies = st.data_editor(Technologies_base.style.format("{:.0f}"))

        #Checkboxes to activate different constraints
        Adequacy = st.checkbox(f"Adequacy (Derated Capacity >= {Peak} MW)")
        Inertia = st.checkbox("Inertia (J>= 750 GW.s)")
        CO2 = st.checkbox("Net-Zero (CO\u2082 intensity <= 50g/kWh)")

        #Adding binary terms to activate selected constraints
        if Adequacy:
            Ad = 1
        else:
            Ad = 0

        if Inertia:
            In = 1
        else:
            In = 0

        if CO2:
            NZ = 1
        else:
            NZ = 0

        
        # Variables (capacity of each technology and energy production by each technology)
        Wind_Cap = cp.Variable(nonneg=True)
        Solar_Cap = cp.Variable(nonneg=True)
        Gas_Cap = cp.Variable(nonneg=True)
        Nuclear_Cap = cp.Variable(nonneg=True)

        Wind_Gen = cp.Variable(nonneg=True)
        Solar_Gen = cp.Variable(nonneg=True)
        Gas_Gen = cp.Variable(nonneg=True)
        Nuclear_Gen = cp.Variable(nonneg=True)

        Caps = cp.hstack([
        Solar_Cap,
        Wind_Cap,
        Gas_Cap,
        Nuclear_Cap
        ])

        Gens = cp.hstack([
            Solar_Gen,
            Wind_Gen,
            Gas_Gen,
            Nuclear_Gen
        ])

        #Extracting data from the technologies data frame to use in the constraints and objective
        E_Costs = Technologies.loc["Energy Cost £/MWh"].values
        C_Costs = Technologies.loc["Capital Cost (£k/MW)"].values
        S_Costs = Technologies.loc["Site Scarcity Cost (£/MW\u00b2)"].values
        Derating = Technologies.loc["Derating Factor (%)"].values / 100
        Inertia = Technologies.loc["Inertia Contant (GW.s/GW)"].values
        Carbon = Technologies.loc["Carbon Intensity (kgCO\u2082/kWh)"].values
        CFs = Technologies.loc["Capacity Factor (%)"].values
         
        #Objective function is the capital cost + operating cost for each technology    
        cost4 = (
                Technologies["Solar"].iloc[0]*Solar_Gen + Technologies["Solar"].iloc[5]*Solar_Cap*1000 + Technologies["Solar"].iloc[6] * cp.square(Solar_Cap)+ 
                Technologies["Wind"].iloc[0]*Wind_Gen + Technologies["Wind"].iloc[5]*Wind_Cap*1000 + Technologies["Wind"].iloc[6] * cp.square(Wind_Cap) +
                Technologies["CCGT Gas"].iloc[0]*Gas_Gen + Technologies["CCGT Gas"].iloc[5]*Gas_Cap*1000 + Technologies["CCGT Gas"].iloc[6]*cp.square(Gas_Cap) +
                Technologies["Nuclear"].iloc[0]*Nuclear_Gen + Technologies["Nuclear"].iloc[5]*Nuclear_Cap*1000 + Technologies["Nuclear"].iloc[6]*cp.square(Nuclear_Cap) 
                )
            
                # Constraints - Security, Inertia, and carbon costraints are toggled. Other constraints are energy balance and power capacity
        NZconstraints = [
            Derating@Caps >= Ad*Peak,
            Inertia@Caps >= In*750,
            Carbon@Gens*(NZ/Energy)<= 50,
            sum(Gens) >= Energy,
            Solar_Gen <= Solar_Cap * 8760 *  Technologies["Solar"].iloc[4]/100,
            Wind_Gen <= Wind_Cap * 8760 *  Technologies["Wind"].iloc[4]/100,
            Gas_Gen <= Gas_Cap * 8760 *  Technologies["CCGT Gas"].iloc[4]/100,
            Nuclear_Gen <= Nuclear_Cap * 8760 *  Technologies["Nuclear"].iloc[4]/100,
            Solar_Gen >= Solar_Cap * 8760 *  Technologies["Solar"].iloc[7]/100,
            Wind_Gen >= Wind_Cap * 8760 *  Technologies["Wind"].iloc[7]/100,
            Gas_Gen >= Gas_Cap * 8760 *  Technologies["CCGT Gas"].iloc[7]/100,
            Nuclear_Gen >= Nuclear_Cap * 8760 *  Technologies["Nuclear"].iloc[7]/100
        ]
                
            # Solve
        prob4 = cp.Problem(cp.Minimize(cost4), NZconstraints)
        prob4.solve()
        Carbon_Intensity = Gens.value@Carbon/Energy

        #Print some key results
        st.metric("Annual Cost", f"£{prob4.value/1e6:.0f}M")
        st.metric("Carbon Intensity",f"{Carbon_Intensity:.0f} kgCO\u2082/kWh")
        st.write(prob4.status)

        #Put results in a data frame for plotting
        Results = pd.DataFrame(
            {"Generation": [Solar_Gen.value/1000, Wind_Gen.value/1000,Gas_Gen.value/1000, Nuclear_Gen.value/1000],
             "Capacity": [Solar_Cap.value, Wind_Cap.value,Gas_Cap.value, Nuclear_Cap.value],
             "Adequacy Contribution": [Solar_Cap.value*Technologies["Solar"].iloc[1]/100,Wind_Cap.value*Technologies["Wind"].iloc[1]/100,Gas_Cap.value*Technologies["CCGT Gas"].iloc[1]/100,Nuclear_Cap.value*Technologies["Nuclear"].iloc[1]/100],
             "Inertia Contribution": [Solar_Gen.value*Technologies["Solar"].iloc[2]/8760,Wind_Gen.value*Technologies["Wind"].iloc[2]/8760,Gas_Gen.value*Technologies["CCGT Gas"].iloc[2]/8760,Nuclear_Gen.value*Technologies["Nuclear"].iloc[2]/8760],
            },
             index=["Solar","Wind","CCGT Gas", "Nuclear"]
        )

        #Create two columns for plots
        col1c, col2c = st.columns(2)

        colours = ["gold", "deepskyblue", "indianred", "limegreen"]

        #Left hand figure shows which generators were used
        with col1c:

            figGen = go.Figure(
                data=[
                    go.Pie(
                        labels=Results.index,
                        values=Results["Generation"],
                        marker_colors=colours,
                        hole=0.3,
                    )
                ]
            )

            figGen.update_layout(
                title="Generation Mix"
            )

            st.plotly_chart(figGen, use_container_width=True)

        with col2c:
            #Right hand figure shows which generators were built
            figCap = go.Figure(
                data=[
                    go.Pie(
                        labels=Results.index,
                        values=Results["Capacity"],
                        marker_colors=colours,
                        hole=0.3,
                    )
                ]
            )

            figCap.update_layout(
                title="Installed Capacity"
            )

            st.plotly_chart(figCap, use_container_width=True)

        st.write("Reached stacked chart")
        figServices = go.Figure()

        colours = {
            "Solar": "gold",
            "Wind": "deepskyblue",
            "CCGT Gas": "indianred",
            "Nuclear": "limegreen"
        }

        for tech in Results.index:

            figServices.add_trace(
                go.Bar(
                    name=tech,
                    x=[
                        "Generation",
                        "Adequacy",
                        "Inertia"
                    ],
                    y=[
                        Results.loc[tech, "Generation"],
                        Results.loc[tech, "Adequacy Contribution"],
                        Results.loc[tech, "Inertia Contribution"],
                    ],
                    marker_color=colours[tech]
                )
            )

        figServices.update_layout(
            title="Technology Contributions",
            barmode="stack",
            xaxis_title="System Service",
            yaxis_title="Contribution"
        )

        st.plotly_chart(
            figServices,
            use_container_width=True
        )

with tab5:

    Example_data = pd.read_csv("Storage example data.csv")

    Wind_Cap_Mult = st.slider("Wind Capacity (MW)",0,10,5)

    Example_data["Wind"] = Example_data["Wind"] * Wind_Cap_Mult

    fig5 = go.Figure()

    fig5.add_trace(
        go.Scatter(
            x=Example_data["Hour"],
            y=Example_data["Demand"],
            name="Demand (MW)",
        )
    )

    fig5.add_trace(
        go.Scatter(
            x=Example_data["Hour"],
            y=Example_data["Wind"],
            name="Wind Generation (MW)"
        )
    )

    st.plotly_chart(
        fig5,
        use_container_width=True
        )

    ES_Power_Cap = st.slider("Energy Storage Power Rating (MW)",1,5,1)*1000
    ES_Hours = st.slider("Energy Storage Capacity (hours)",1,5,2)

    #Variables for optimization problem
    Thermal_Gen = cp.Variable(168,nonneg=True)
    Wind_Gen = cp.Variable(168,nonneg=True)
    ES_Gen = cp.Variable(168)
    ES_Soc = cp.Variable(169,nonneg = True)
    Wind_Cap = cp.Parameter(168, value=Example_data["Wind"].values)
    Demand = cp.Parameter(168, value=Example_data["Demand"].values)

    #Constraints
    ES_Constraints = [
        Wind_Gen + Thermal_Gen + ES_Gen == Demand,
        Wind_Gen<=Wind_Cap,
        ES_Soc[1:] == ES_Soc[:-1] - ES_Gen/(ES_Power_Cap*ES_Hours),
        ES_Soc[0] == 0.5,
        ES_Soc[168] == 0.5,
        ES_Soc<=1,
        ES_Gen <= ES_Power_Cap,
        ES_Gen >= -ES_Power_Cap,
    ]

    cost5 = cp.sum(
            300 + 30*Thermal_Gen + 0.03*cp.square(Thermal_Gen)
    )

    prob5 = cp.Problem(cp.Minimize(cost5), ES_Constraints)
    prob5.solve(solver=cp.CLARABEL)

    Dispatch = pd.DataFrame(
        {
            "Wind": Wind_Gen.value,
            "Thermal": Thermal_Gen.value,
            "Battery": ES_Gen.value,
        }
    )

    Battery_Discharge = np.maximum(
        ES_Gen.value,
        0
    )

    Battery_Charge = np.minimum(
        ES_Gen.value,
        0
    )

    figDispatch = go.Figure()

    figDispatch.add_trace(
        go.Bar(
            x=np.arange(168),
            y=Battery_Discharge,
            name="Battery Discharge",
            marker_color="limegreen"
        )
    )

    figDispatch.add_trace(
        go.Bar(
            x=np.arange(168),
            y=Wind_Gen.value,
            name="Wind",
            marker_color="deepskyblue"
        )
    )

    figDispatch.add_trace(
        go.Bar(
            x=np.arange(168),
            y=Thermal_Gen.value,
            name="Thermal",
            marker_color="indianred"
        )
    )

    figDispatch.add_trace(
        go.Bar(
            x=np.arange(168),
            y=Battery_Charge,
            name="Battery Charge",
            marker_color="darkgreen"
        )
    )

    figDispatch.add_trace(
        go.Scatter(
            x=np.arange(168),
            y=Demand.value,
            mode="lines",
            name="Demand",
            line=dict(color="black", width=3)
        )
    )

    figDispatch.update_layout(
        title="System Dispatch",
        barmode="relative",
        xaxis_title="Hour",
        yaxis_title="Power (MW)"
    )

    st.plotly_chart(
        figDispatch,
        use_container_width=True
    )

    figSoc = go.Figure()

    figSoc.add_trace(
        go.Scatter(
            x=np.arange(len(ES_Soc.value)),
            y=ES_Soc.value,
            mode="lines",
            name="SoC",
            line=dict(color="darkgreen", width=3),
        )
    )

    figSoc.add_hline(y=1, line_dash="dash")
    figSoc.add_hline(y=0, line_dash="dash")

    figSoc.update_layout(
        title="Battery State of Charge",
        xaxis_title="Hour",
        yaxis_title="State of Charge (p.u.)",
        yaxis_range=[0, 1.05],
    )

    st.plotly_chart(
        figSoc,
        use_container_width=True,
    )

    Marginal_Cost = -ES_Constraints[0].dual_value

    #Calculate dispatch without storage
    Example_data["Base_Dispatch"] = Example_data["Demand"]-Example_data["Wind"]
    Example_data["Base_Dispatch"] = Example_data["Base_Dispatch"].clip(lower=0)
    Example_data["Base_MC"] = 30 + 0.06 * Example_data["Base_Dispatch"]
    Example_data.loc[Example_data["Base_Dispatch"] == 0,
                    "Base_MC"
                    ] = 0
    Base_total_cost = (300 + 30*Example_data["Base_Dispatch"] + 0.03*(Example_data["Base_Dispatch"])**2).sum()

    figMC = go.Figure()

    figMC.add_trace(
        go.Scatter(
            x=np.arange(168),
            y=Marginal_Cost,
            mode="lines",
            name="Marginal Cost with storage",
            line=dict(color="black"),
        )
    )

    figMC.add_trace(
        go.Scatter(
            x=np.arange(168),
            y=Example_data["Base_MC"],
            mode="lines",
            name="Marginal Cost without storage",
            line=dict(color="Grey"),
        )
    )

    figMC.update_layout(
        title="System Marginal Cost",
        xaxis_title="Hour",
        yaxis_title="£/MWh",
    )

    st.plotly_chart(
        figMC,
        use_container_width=True,
    )

    Total_Cost = prob5.value

    Wind_Energy = np.sum(Wind_Gen.value)
    Thermal_Energy = np.sum(Thermal_Gen.value)

    Battery_Charge = np.sum(
        np.maximum(-ES_Gen.value, 0)
    )

    Battery_Discharge = np.sum(
        np.maximum(ES_Gen.value, 0)
    )

    st.metric(
        "Total Cost With Storage",
        f"£{Total_Cost:,.0f}"
    )

    Storage_Saving = Base_total_cost-Total_Cost

    st.metric(
        "Total Cost Without Storage",
        f"£{Base_total_cost:,.0f}"
    )

    st.metric(
        "Storage Saving",
        f"£{Storage_Saving:,.0f}"
    )

with tab6:
    Example_data2 = pd.read_csv("Storage example data.csv")

    Wind_Cap_Mult2 = st.slider("VRE Capacity (MW)",0,9,5)
    
    Example_data2["Wind"] = Example_data2["Wind"] * Wind_Cap_Mult2
    
    fig6 = go.Figure()

    fig6.add_trace(
        go.Scatter(
            x=Example_data2["Hour"],
            y=Example_data2["Demand"],
            name="Demand (MW)",
        )
    )

    fig6.add_trace(
        go.Scatter(
            x=Example_data2["Hour"],
            y=Example_data2["Wind"],
            name="VRE Capacity (MW)"
        )
    )

    st.plotly_chart(
        fig6,
        use_container_width=True
        )

        #Variables for optimization problem
    Bio_Gen = cp.Variable(168,nonneg=True)
    Wind_Gen = cp.Variable(168,nonneg=True)
    Gas_Gen = cp.Variable(168,nonneg=True)
    Wind_Cap = cp.Parameter(168, value=Example_data2["Wind"].values)
    Demand = cp.Parameter(168, value=Example_data2["Demand"].values)

    #Constraints
    VRE_Constraints = [
        Wind_Gen + Gas_Gen + Bio_Gen == Demand,
        Wind_Gen<=Wind_Cap,

    ]

    cost6 = cp.sum(
            100 + 30*Gas_Gen + 0.1*cp.square(Gas_Gen) + 200 + 50*Bio_Gen + 0.1*cp.square(Bio_Gen)
    )

    prob6 = cp.Problem(cp.Minimize(cost6), VRE_Constraints)
    prob6.solve(solver=cp.CLARABEL)

    Dispatch_VRE = pd.DataFrame(
        {
            "VRE": Wind_Gen.value,
            "Gas": Gas_Gen.value,
            "Bio": Bio_Gen.value,
            "Curtailment": Wind_Cap.value-Wind_Gen.value
        }
    )

        
    figDispatch_VRE = go.Figure()

    figDispatch_VRE.add_trace(
        go.Bar(
            x=np.arange(168),
            y=Wind_Gen.value,
            name="VRE",
            marker_color="darkgreen"
        )
    )

    figDispatch_VRE.add_trace(
        go.Bar(
            x=np.arange(168),
            y=Gas_Gen.value,
            name="Gas",
            marker_color="indianred"
        )
    )

    figDispatch_VRE.add_trace(
        go.Bar(
            x=np.arange(168),
            y=Bio_Gen.value,
            name="Bio",
            marker_color="deepskyblue"
        )
    )

    figDispatch_VRE.add_trace(
        go.Scatter(
            x=np.arange(168),
            y=Demand.value,
            mode="lines",
            name="Demand",
            line=dict(color="black", width=3)
        )
    )

    figDispatch_VRE.update_layout(
        title="System Dispatch",
        barmode="relative",
        xaxis_title="Hour",
        yaxis_title="Power (MW)"
    )

    st.plotly_chart(
        figDispatch_VRE,
        use_container_width=True
    )

    figCurtailment = go.Figure()

    figCurtailment.add_trace(
            go.Scatter(
                x=Example_data2["Hour"],
                y=Dispatch_VRE["Curtailment"],
                name="Curtailed VRE (MW)",
            )
        )

    figCurtailment.update_layout(
    title="Curtailed VRE",
    xaxis_title="Hour",
    yaxis_title="MW",
    )

    st.plotly_chart(
    figCurtailment,
    use_container_width=True
    )